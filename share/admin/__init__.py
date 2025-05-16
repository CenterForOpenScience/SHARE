from django.apps import apps
from django.contrib import admin
from django.urls import path

from oauth2_provider.models import AccessToken

from share.admin.celery import CeleryTaskResultAdmin
from share.admin.search import search_indexes_view, search_index_mappings_view
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many, SourceConfigFilter
from share.models import (
    CeleryTaskResult,
    FeatureFlag,
    IndexBackfill,
    ShareUser,
    SiteBanner,
    Source,
    SourceConfig,
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


class AccessTokenAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('token', 'user', 'scope')


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


@linked_fk('source')
class SourceConfigAdmin(admin.ModelAdmin):
    list_display = ('label', 'source_', 'version', 'enabled',)
    list_select_related = ('source',)
    search_fields = ['label', 'source__name', 'source__long_title']
    actions = ['schedule_derive']

    def source_(self, obj):
        return obj.source.long_title

    def enabled(self, obj):
        return not obj.disabled
    enabled.boolean = True  # type: ignore[attr-defined]

    @admin.action(description='schedule re-derive of all cards for each selected source config')
    def schedule_derive(self, request, queryset):
        for _id in queryset.values_list('id', flat=True):
            digestive_tract.task__schedule_derive_for_source_config.delay(_id)


@linked_fk('user')
class SourceAdmin(admin.ModelAdmin):
    search_fields = ('name', 'long_title')
    readonly_fields = ('access_token',)

    def access_token(self, obj):
        tokens = obj.user.oauth2_provider_accesstoken.all()
        if tokens:
            return tokens[0].token
        return None


@linked_fk('source_config')
@linked_fk('focus_identifier')
@linked_many('formattedmetadatarecord_set', defer=('formatted_metadata',))
@linked_many('indexcard_set')
class SourceUniqueIdentifierAdmin(admin.ModelAdmin):
    readonly_fields = ('identifier',)
    paginator = TimeLimitedPaginator
    actions = ('delete_cards_for_suid',)
    list_filter = (SourceConfigFilter,)
    list_select_related = ('source_config',)
    show_full_result_count = False
    search_fields = ('identifier',)

    def delete_cards_for_suid(self, request, queryset):
        for suid in queryset:
            digestive_tract.expel_suid(suid)

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)

        return (
            queryset.filter(identifier=search_term),
            False,  # no duplicates expected
        )


class IndexBackfillAdmin(admin.ModelAdmin):
    readonly_fields = (
        'index_strategy_name',
        'strategy_checksum',
        'error_type',
        'error_message',
        'error_context',
    )
    paginator = TimeLimitedPaginator
    list_display = ('index_strategy_name', 'backfill_status', 'created', 'modified', 'strategy_checksum')
    show_full_result_count = False
    search_fields = ('index_strategy_name', 'strategy_checksum',)
    actions = ('reset_to_initial',)

    def reset_to_initial(self, request, queryset):
        queryset.update(backfill_status=IndexBackfill.INITIAL)


class FeatureFlagAdmin(admin.ModelAdmin):
    readonly_fields = ('name',)
    search_fields = ('name',)
    list_display = ('name', 'is_up', 'is_defined')
    list_editable = ('is_up',)


admin_site.register(AccessToken, AccessTokenAdmin)
admin_site.register(CeleryTaskResult, CeleryTaskResultAdmin)
admin_site.register(FeatureFlag, FeatureFlagAdmin)
admin_site.register(IndexBackfill, IndexBackfillAdmin)
admin_site.register(ShareUser, ShareUserAdmin)
admin_site.register(SiteBanner, SiteBannerAdmin)
admin_site.register(Source, SourceAdmin)
admin_site.register(SourceConfig, SourceConfigAdmin)
admin_site.register(SourceUniqueIdentifier, SourceUniqueIdentifierAdmin)
