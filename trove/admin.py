from __future__ import annotations
from typing import Any
from django.contrib import admin
from django.utils.html import format_html

from share.admin import admin_site
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many
from share.search.index_messenger import IndexMessenger
from trove.models import (
    ArchivedResourceDescription,
    DerivedIndexcard,
    Indexcard,
    LatestResourceDescription,
    ResourceIdentifier,
    SupplementaryResourceDescription,
)


@admin.register(ResourceIdentifier, site=admin_site)
@linked_many('suid_set')
@linked_many('indexcard_set')
class ResourceIdentifierAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'sufficiently_unique_iri',
    )
    paginator = TimeLimitedPaginator
    list_display = ('sufficiently_unique_iri', 'scheme_list', 'created', 'modified')
    show_full_result_count = False
    search_fields = ('sufficiently_unique_iri',)


@admin.register(Indexcard, site=admin_site)
@linked_many('archived_description_set', defer=('rdf_as_turtle',))
@linked_many('supplementary_description_set', defer=('rdf_as_turtle',))
@linked_many('derived_indexcard_set', defer=('derived_text',))
@linked_fk('latest_resource_description')
@linked_fk('source_record_suid')
@linked_many('focustype_identifier_set')
@linked_many('focus_identifier_set')
class IndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'uuid',
        'created',
        'modified',
        'deleted',
    )
    paginator = TimeLimitedPaginator
    list_display = ('uuid', 'source_record_suid', 'created', 'modified')
    show_full_result_count = False
    search_fields = ('uuid',)
    list_select_related = ('source_record_suid',)
    list_filter = ('deleted', 'source_record_suid__source_config')
    actions = ('_freshen_index',)

    def _freshen_index(self, queryset: list[Indexcard]) -> None:
        IndexMessenger().notify_indexcard_update(queryset)
    _freshen_index.short_description = 'freshen indexcard in search index'  # type: ignore[attr-defined]


@admin.register(LatestResourceDescription, site=admin_site)
@linked_fk('indexcard')
class LatestResourceDescriptionAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'turtle_checksum_iri',
        'focus_iri',
        'rdf_as_turtle__pre',
    )
    exclude = ('rdf_as_turtle',)
    paginator = TimeLimitedPaginator
    list_display = ('indexcard', 'created', 'modified')
    list_select_related = ('indexcard',)
    show_full_result_count = False

    def rdf_as_turtle__pre(self, instance: Any) -> str:
        return format_html('<pre>{}</pre>', instance.rdf_as_turtle)
    rdf_as_turtle__pre.short_description = 'rdf as turtle'  # type: ignore[attr-defined]


@admin.register(ArchivedResourceDescription, site=admin_site)
@linked_fk('indexcard')
class ArchivedResourceDescriptionAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'turtle_checksum_iri',
        'focus_iri',
        'rdf_as_turtle__pre',
    )
    exclude = ('rdf_as_turtle',)
    paginator = TimeLimitedPaginator
    list_display = ('id', 'indexcard', 'created', 'modified')
    list_select_related = ('indexcard',)
    show_full_result_count = False

    def rdf_as_turtle__pre(self, instance: Any) -> str:
        return format_html('<pre>{}</pre>', instance.rdf_as_turtle)
    rdf_as_turtle__pre.short_description = 'rdf as turtle'  # type: ignore[attr-defined]


@admin.register(SupplementaryResourceDescription, site=admin_site)
@linked_fk('indexcard')
@linked_fk('supplementary_suid')
class SupplementaryResourceDescriptionAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'turtle_checksum_iri',
        'focus_iri',
        'rdf_as_turtle__pre',
    )
    exclude = ('rdf_as_turtle',)
    paginator = TimeLimitedPaginator
    list_display = ('id', 'indexcard', 'created', 'modified')
    list_select_related = ('indexcard',)
    show_full_result_count = False

    def rdf_as_turtle__pre(self, instance: SupplementaryResourceDescription) -> str:
        return format_html('<pre>{}</pre>', instance.rdf_as_turtle)
    rdf_as_turtle__pre.short_description = 'rdf as turtle'  # type: ignore[attr-defined]


@admin.register(DerivedIndexcard, site=admin_site)
@linked_fk('upriver_indexcard')
@linked_fk('deriver_identifier')
class DerivedIndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('id', 'upriver_indexcard', 'deriver_identifier',)
    list_select_related = ('upriver_indexcard',)
    show_full_result_count = False
