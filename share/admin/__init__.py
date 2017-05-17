from furl import furl

from django import forms
from django.conf.urls import url
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import AdminDateWidget
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join, mark_safe

from oauth2_provider.models import AccessToken

from share import tasks
from share.admin.celery import CeleryTaskResultAdmin
from share.admin.readonly import ReadOnlyAdmin
from share.admin.share_objects import CreativeWorkAdmin, SubjectAdmin
from share.admin.util import FuzzyPaginator
from share.harvest.scheduler import HarvestScheduler
from share.models.banner import SiteBanner
from share.models.celery import CeleryTaskResult
from share.models.change import ChangeSet
from share.models.core import NormalizedData, ShareUser
from share.models.creative import AbstractCreativeWork
from share.models.ingest import RawDatum, Source, SourceConfig, Harvester, Transformer
from share.models.logs import HarvestLog
from share.models.meta import Subject, SubjectTaxonomy
from share.models.registration import ProviderRegistration
from share.models.sources import SourceStat


admin.site.register(AbstractCreativeWork, CreativeWorkAdmin)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(CeleryTaskResult, CeleryTaskResultAdmin)


class NormalizedDataAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]
    raw_id_fields = ('raw', 'tasks',)


class ChangeSetSubmittedByFilter(SimpleListFilter):
    title = 'Source'
    parameter_name = 'source_id'

    def lookups(self, request, model_admin):
        return ShareUser.objects.filter(is_active=True).values_list('id', 'username')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(normalized_data__source_id=self.value())
        return queryset


class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ('status_', 'count_changes', 'submitted_by', 'submitted_at')
    actions = ['accept_changes']
    list_filter = ['status', ChangeSetSubmittedByFilter]
    raw_id_fields = ('normalized_data',)

    def submitted_by(self, obj):
        return obj.normalized_data.source
    submitted_by.short_description = 'submitted by'

    def count_changes(self, obj):
        return obj.changes.count()
    count_changes.short_description = 'number of changes'

    def status_(self, obj):
        return ChangeSet.STATUS[obj.status].title()


class RawDatumAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_select_related = ('suid__source_config', )
    list_display = ('id', 'identifier', 'source_config_label', 'datestamp', 'date_created', 'date_modified', )

    def identifier(self, obj):
        return obj.suid.identifier

    def source_config_label(self, obj):
        return obj.suid.source_config.label


class AccessTokenAdmin(admin.ModelAdmin):
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


class SourceConfigFilter(admin.SimpleListFilter):
    title = 'Source Config'
    parameter_name = 'source_config'

    def lookups(self, request, model_admin):
        # TODO make this into a cool hierarchy deal
        # return SourceConfig.objects.select_related('source').values_list('
        return SourceConfig.objects.order_by('label').values_list('id', 'label')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_config=self.value())


class HarvestLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'label', 'share_version', 'status_', 'start_date_', 'end_date_', 'harvest_log_actions', )
    list_filter = ('status', SourceConfigFilter, )
    list_select_related = ('source_config__source', )
    readonly_fields = ('harvest_log_actions',)
    actions = ('restart_tasks', )
    show_full_result_count = False
    paginator = FuzzyPaginator

    STATUS_COLORS = {
        HarvestLog.STATUS.created: 'blue',
        HarvestLog.STATUS.started: 'cyan',
        HarvestLog.STATUS.failed: 'red',
        HarvestLog.STATUS.succeeded: 'green',
        HarvestLog.STATUS.rescheduled: 'goldenrod',
        HarvestLog.STATUS.forced: 'maroon',
        HarvestLog.STATUS.skipped: 'orange',
        HarvestLog.STATUS.retried: 'darkseagreen',
        HarvestLog.STATUS.cancelled: 'grey',
    }

    def source(self, obj):
        return obj.source_config.source.long_title

    def label(self, obj):
        return obj.source_config.label

    def start_date_(self, obj):
        return obj.start_date.isoformat()

    def end_date_(self, obj):
        return obj.end_date.isoformat()

    def status_(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: {}">{}</span>',
            self.STATUS_COLORS[obj.status],
            HarvestLog.STATUS[obj.status].title(),
        )

    def restart_tasks(self, request, queryset):
        queryset.update(status=HarvestLog.STATUS.created)
    restart_tasks.short_description = 'Re-enqueue'

    def harvest_log_actions(self, obj):
        url = furl(reverse('admin:source-config-harvest', args=[obj.source_config_id]))
        url.args['start'] = self.start_date_(obj)
        url.args['end'] = self.end_date_(obj)
        url.args['superfluous'] = True
        return format_html('<a class="button" href="{}">Restart</a>', url.url)
    harvest_log_actions.short_description = 'Actions'


class HarvestForm(forms.Form):
    start = forms.DateField(widget=AdminDateWidget())
    end = forms.DateField(widget=AdminDateWidget())
    superfluous = forms.BooleanField(required=False)

    def clean(self):
        super().clean()
        if self.cleaned_data['start'] > self.cleaned_data['end']:
            raise forms.ValidationError('Start date cannot be after end date.')


class SourceConfigAdmin(admin.ModelAdmin):
    list_display = ('label', 'source_', 'version', 'enabled', 'source_config_actions')
    list_select_related = ('source',)
    readonly_fields = ('source_config_actions',)
    search_fields = ['label', 'source__name', 'source__long_title']

    def source_(self, obj):
        return obj.source.long_title

    def enabled(self, obj):
        return not obj.disabled
    enabled.boolean = True

    def get_urls(self):
        return [
            url(
                r'^(?P<config_id>.+)/harvest/$',
                self.admin_site.admin_view(self.harvest),
                name='source-config-harvest'
            )
        ] + super().get_urls()

    def source_config_actions(self, obj):
        if obj.harvester_id is None:
            return ''
        return format_html(
            '<a class="button" href="{}">Harvest</a>',
            reverse('admin:source-config-harvest', args=[obj.pk]),
        )
    source_config_actions.short_description = 'Actions'

    def harvest(self, request, config_id):
        config = self.get_object(request, config_id)
        if config.harvester_id is None:
            raise ValueError('You need a harvester to harvest.')

        if request.method == 'POST':
            form = HarvestForm(request.POST)
            if form.is_valid():
                for log in HarvestScheduler(config).range(form.cleaned_data['start'], form.cleaned_data['end']):
                    tasks.harvest.apply_async((), {'log_id': log.id, 'superfluous': form.cleaned_data['superfluous']})

                self.message_user(request, 'Started harvesting {}!'.format(config.label))
                url = reverse('admin:share_harvestlog_changelist', current_app=self.admin_site.name)
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


class SourceAdminInline(admin.StackedInline):
    model = Source


class ShareUserAdmin(admin.ModelAdmin):
    inlines = (SourceAdminInline,)


class SourceAddForm(forms.ModelForm):

    title = forms.CharField(min_length=3, max_length=255, help_text='What this source will be displayed as to the end user. Must be unique.')
    url = forms.URLField(min_length=11, max_length=255, help_text='The home page or canonical URL for this source, make sure it is unique!.\nThe reverse DNS notation prepended with "sources." will be used to create a user for this source. IE share.osf.io -> sources.io.osf.share')

    class Meta:
        model = Source
        exclude = ('access_token', )
        fields = ('title', 'url', 'icon', )

    def validate_unique(self):
        # Forces validation checks on every field
        try:
            self.instance.validate_unique()
        except forms.ValidationError as e:
            # Translate field names because I'm a bad person
            if 'long_title' in e.error_dict:
                e.error_dict['title'] = e.error_dict.pop('long_title')
            if 'name' in e.error_dict:
                e.error_dict['url'] = e.error_dict.pop('name')
            if 'home_page' in e.error_dict:
                e.error_dict['url'] = e.error_dict.pop('home_page')
            self._update_errors(e)

    def _post_clean(self):
        if not self._errors:
            self.instance.home_page = self.cleaned_data['url'].lower().strip('/')
            self.instance.long_title = self.cleaned_data.pop('title')
            self.instance.name = '.'.join(reversed(self.instance.home_page.split('//')[1].split('.')))
        return super()._post_clean()

    def save(self, commit=True):
        instance = super().save(commit=False)

        user = ShareUser.objects.create_user(username='sources.' + instance.name, save=commit)
        user.set_unusable_password()
        instance.user = user

        if commit:
            instance.save()

        return instance


class SourceAdmin(admin.ModelAdmin):
    search_fields = ('name', 'long_title')
    readonly_fields = ('access_token', )

    def add_view(self, *args, **kwargs):
        self.form = SourceAddForm
        return super().add_view(*args, **kwargs)

    def save_model(self, request, obj, form, change):
        if obj.user and not (obj.user_id or obj.user.id):
            obj.user.save()
            obj.user_id = obj.user.id  # Django is weird
        obj.save()

    def access_token(self, obj):
        tokens = obj.user.accesstoken_set.all()
        if tokens:
            return tokens[0].token
        return None


class SubjectTaxonomyAdmin(admin.ModelAdmin):
    readonly_fields = ('source', 'subject_links',)
    fields = ('source', 'is_deleted', 'subject_links')
    list_fields = ('source__name',)
    list_select_related = ('source', )

    def subject_links(self, obj):
        def recursive_link_list(subjects):
            if not subjects:
                return ''
            items = format_html_join(
                '', '<li style="list-style: square;"><a href="{}">{}</a>{}</li>',
                (
                    (
                        reverse('admin:share_subject_change', args=(s.id,)),
                        s.name,
                        mark_safe(recursive_link_list(list(s.children.all())))
                    ) for s in sorted(subjects, key=lambda s: s.name)
                )
            )
            return format_html('<ul style="margin-left: 10px;">{}</ul>', mark_safe(items))
        roots = obj.subject_set.filter(parent__isnull=True).prefetch_related('children', 'children__children', 'children__children__children')
        return recursive_link_list(list(roots))
    subject_links.short_description = 'Subjects'


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


admin.site.unregister(AccessToken)
admin.site.register(AccessToken, AccessTokenAdmin)

admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(HarvestLog, HarvestLogAdmin)
admin.site.register(NormalizedData, NormalizedDataAdmin)
admin.site.register(ProviderRegistration, ProviderRegistrationAdmin)
admin.site.register(RawDatum, RawDatumAdmin)
admin.site.register(SiteBanner, SiteBannerAdmin)

admin.site.register(Harvester)
admin.site.register(ShareUser, ShareUserAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(SourceConfig, SourceConfigAdmin)
admin.site.register(SubjectTaxonomy, SubjectTaxonomyAdmin)
admin.site.register(SourceStat, SourceStatAdmin)
admin.site.register(Transformer)
