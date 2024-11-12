from prettyjson import PrettyJSONWidget

from django import forms
from django.apps import apps
from django.urls import re_path as url
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from oauth2_provider.models import AccessToken

from share import tasks
from share.admin.celery import CeleryTaskResultAdmin
from share.admin.jobs import HarvestJobAdmin
from share.admin.readonly import ReadOnlyAdmin
from share.admin.search import search_indexes_view, search_index_mappings_view
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many, SourceConfigFilter
from share.harvest.scheduler import HarvestScheduler
from share.models import (
    CeleryTaskResult,
    DateTimeAwareJSONField,
    FeatureFlag,
    FormattedMetadataRecord,
    HarvestJob,
    IndexBackfill,
    NormalizedData,
    ProviderRegistration,
    RawDatum,
    ShareUser,
    SiteBanner,
    Source,
    SourceConfig,
    SourceStat,
    SourceUniqueIdentifier,
)
from trove import digestive_tract


class ShareAdminSite(admin.AdminSite):
    def get_urls(self):
        return [
            path(
                'search-indexes',
                self.admin_view(search_indexes_view),
                name='search-indexes',
            ),
            path(
                'search-index-mappings/<index_name>',
                self.admin_view(search_index_mappings_view),
                name='search-index-mappings',
            ),
            *super().get_urls(),
        ]


admin_site = ShareAdminSite()

admin_site.register(apps.get_app_config('django_celery_beat').get_models())


class ShareUserAdmin(admin.ModelAdmin):
    search_fields = ['username']


@linked_fk('raw')
@linked_fk('source')
class NormalizedDataAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]
    raw_id_fields = ('tasks',)
    paginator = TimeLimitedPaginator
    formfield_overrides = {
        DateTimeAwareJSONField: {
            'widget': PrettyJSONWidget(attrs={
                'initial': 'parsed',
                'cols': 120,
                'rows': 20
            })
        }
    }


@linked_fk('suid')
class RawDatumAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_select_related = ('suid__source_config', )
    list_display = ('id', 'identifier', 'source_config_label', 'datestamp', 'date_created', 'date_modified', )
    readonly_fields = ('datum__pre', 'sha256')
    exclude = ('datum',)
    raw_id_fields = ('jobs',)
    paginator = TimeLimitedPaginator

    def identifier(self, obj):
        return obj.suid.identifier

    def source_config_label(self, obj):
        return obj.suid.source_config.label

    def datum__pre(self, instance):
        return format_html('<pre>{}</pre>', instance.datum)
    datum__pre.short_description = 'datum'


class AccessTokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('token', 'user', 'scope')


class ProviderRegistrationAdmin(ReadOnlyAdmin):
    list_display = ('source_name', 'status_', 'submitted_at', 'submitted_by', 'direct_source')
    list_filter = ('direct_source', 'status',)
    readonly_fields = ('submitted_at', 'submitted_by',)

    def status_(self, obj):
        return ProviderRegistration.STATUS[obj.status].title()


class SiteBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'color', 'icon', 'active')
    list_editable = ('active',)
    ordering = ('-active', '-last_modified_at')
    readonly_fields = ('created_at', 'created_by', 'last_modified_at', 'last_modified_by')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)


class HarvestForm(forms.Form):
    start = forms.DateField(widget=AdminDateWidget())
    end = forms.DateField(widget=AdminDateWidget())
    superfluous = forms.BooleanField(required=False)

    def clean(self):
        super().clean()
        if self.cleaned_data['start'] > self.cleaned_data['end']:
            raise forms.ValidationError('Start date cannot be after end date.')


@linked_fk('source')
class SourceConfigAdmin(admin.ModelAdmin):
    list_display = ('label', 'source_', 'version', 'enabled', 'button_actions')
    list_select_related = ('source',)
    readonly_fields = ('button_actions',)
    search_fields = ['label', 'source__name', 'source__long_title']
    actions = ['schedule_full_ingest']

    def source_(self, obj):
        return obj.source.long_title

    def enabled(self, obj):
        return not obj.disabled
    enabled.boolean = True

    @admin.action(description='schedule re-ingest of all raw data for each source config')
    def schedule_full_ingest(self, request, queryset):
        for _id in queryset.values_list('id', flat=True):
            digestive_tract.task__schedule_extract_and_derive_for_source_config.delay(_id)

    def get_urls(self):
        return [
            url(
                r'^(?P<config_id>.+)/harvest/$',
                self.admin_site.admin_view(self.harvest),
                name='source-config-harvest'
            ),
            url(
                r'^(?P<config_id>.+)/ingest/$',
                self.admin_site.admin_view(self.start_ingest),
                name='source-config-ingest'
            )
        ] + super().get_urls()

    def button_actions(self, obj):
        return format_html(
            ' '.join((
                ('<a class="button" href="{harvest_href}">Harvest</a>' if obj.harvester_key else ''),
                ('<a class="button" href="{ingest_href}">Ingest</a>' if not obj.disabled else ''),
            )),
            harvest_href=reverse('admin:source-config-harvest', args=[obj.pk]),
            ingest_href=reverse('admin:source-config-ingest', args=[obj.pk]),
        )
    button_actions.short_description = 'Buttons'

    def harvest(self, request, config_id):
        config = self.get_object(request, config_id)
        if config.harvester_key is None:
            raise ValueError('You need a harvester to harvest.')
        if request.method == 'POST':
            form = HarvestForm(request.POST)
            if form.is_valid():
                for job in HarvestScheduler(config, claim_jobs=True).range(form.cleaned_data['start'], form.cleaned_data['end']):
                    tasks.harvest.apply_async((), {'job_id': job.id, 'superfluous': form.cleaned_data['superfluous']})
                self.message_user(request, 'Started harvesting {}!'.format(config.label))
                url = reverse('admin:share_harvestjob_changelist', current_app=self.admin_site.name)
                return HttpResponseRedirect(url)
        else:
            initial = {'start': config.earliest_date, 'end': timezone.now().date()}
            for field in HarvestForm.base_fields.keys():
                if field in request.GET:
                    initial[field] = request.GET[field]
            form = HarvestForm(initial=initial)
        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['form'] = form
        context['source_config'] = config
        context['title'] = 'Harvest {}'.format(config.label)
        return TemplateResponse(request, 'admin/harvest.html', context)

    def start_ingest(self, request, config_id):
        config = self.get_object(request, config_id)
        if request.method == 'POST':
            digestive_tract.task__schedule_extract_and_derive_for_source_config.delay(config.pk)
            url = reverse(
                'admin:share_sourceconfig_changelist',
                current_app=self.admin_site.name,
            )
            return HttpResponseRedirect(url)
        else:
            context = self.admin_site.each_context(request)
            context['source_config'] = config
            return TemplateResponse(request, 'admin/start-ingest.html', context)


@linked_fk('user')
class SourceAdmin(admin.ModelAdmin):
    search_fields = ('name', 'long_title')
    readonly_fields = ('access_token',)

    def access_token(self, obj):
        tokens = obj.user.oauth2_provider_accesstoken.all()
        if tokens:
            return tokens[0].token
        return None


class SourceStatAdmin(admin.ModelAdmin):
    search_fields = ('config__label', 'config__source__long_title')
    list_display = ('label', 'date_created', 'base_urls_match', 'earliest_datestamps_match', 'response_elapsed_time', 'response_status_code', 'grade_')
    list_filter = ('grade', 'response_status_code', 'config__label')

    GRADE_COLORS = {
        0: 'red',
        5: 'orange',
        10: 'green',
    }
    GRADE_LETTERS = {
        0: 'F',
        5: 'C',
        10: 'A',
    }

    def source(self, obj):
        return obj.config.source.long_title

    def label(self, obj):
        return obj.config.label

    def grade_(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: {}">{}</span>',
            self.GRADE_COLORS[obj.grade],
            self.GRADE_LETTERS[obj.grade],
        )


@linked_fk('source_config')
@linked_fk('focus_identifier')
@linked_many('formattedmetadatarecord_set', defer=('formatted_metadata',))
@linked_many('raw_data', defer=('datum',))
@linked_many('indexcard_set')
class SourceUniqueIdentifierAdmin(admin.ModelAdmin):
    readonly_fields = ('identifier',)
    paginator = TimeLimitedPaginator
    actions = ('reingest', 'delete_cards_for_suid')
    list_filter = (SourceConfigFilter,)
    list_select_related = ('source_config',)
    show_full_result_count = False
    search_fields = ('identifier',)

    def reingest(self, request, queryset):
        _raw_id_queryset = (
            RawDatum.objects
            .latest_by_suid_queryset(queryset)
            .values_list('id', flat=True)
        )
        for _raw_id in _raw_id_queryset:
            digestive_tract.task__extract_and_derive.delay(raw_id=_raw_id)

    def delete_cards_for_suid(self, request, queryset):
        for suid in queryset:
            FormattedMetadataRecord.objects.delete_formatted_records(suid)
            digestive_tract.expel_suid(suid)

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)

        return (
            queryset.filter(identifier=search_term),
            False,  # no duplicates expected
        )


@linked_fk('suid')
class FormattedMetadataRecordAdmin(admin.ModelAdmin):
    readonly_fields = ('record_format',)
    paginator = TimeLimitedPaginator
    show_full_result_count = False


class IndexBackfillAdmin(admin.ModelAdmin):
    readonly_fields = (
        'index_strategy_name',
        'specific_indexname',
        'error_type',
        'error_message',
        'error_context',
    )
    paginator = TimeLimitedPaginator
    list_display = ('index_strategy_name', 'backfill_status', 'created', 'modified', 'specific_indexname')
    show_full_result_count = False
    search_fields = ('index_strategy_name', 'specific_indexname',)
    actions = ('reset_to_initial',)

    def reset_to_initial(self, request, queryset):
        queryset.update(backfill_status=IndexBackfill.INITIAL)


class FeatureFlagAdmin(admin.ModelAdmin):
    readonly_fields = ('name',)
    search_fields = ('name',)
    list_display = ('name', 'is_up', 'is_defined')


admin_site.register(AccessToken, AccessTokenAdmin)
admin_site.register(CeleryTaskResult, CeleryTaskResultAdmin)
admin_site.register(FeatureFlag, FeatureFlagAdmin)
admin_site.register(FormattedMetadataRecord, FormattedMetadataRecordAdmin)
admin_site.register(HarvestJob, HarvestJobAdmin)
admin_site.register(IndexBackfill, IndexBackfillAdmin)
admin_site.register(NormalizedData, NormalizedDataAdmin)
admin_site.register(ProviderRegistration, ProviderRegistrationAdmin)
admin_site.register(RawDatum, RawDatumAdmin)
admin_site.register(ShareUser, ShareUserAdmin)
admin_site.register(SiteBanner, SiteBannerAdmin)
admin_site.register(Source, SourceAdmin)
admin_site.register(SourceConfig, SourceConfigAdmin)
admin_site.register(SourceStat, SourceStatAdmin)
admin_site.register(SourceUniqueIdentifier, SourceUniqueIdentifierAdmin)
