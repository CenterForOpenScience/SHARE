from django.contrib import admin

from share.admin import admin_site
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many
from trove.models import ResourceIdentifier, Indexcard, LatestIndexcardRdf, ArchivedIndexcardRdf, DerivedIndexcard


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
@linked_many('derived_indexcard_set')
@linked_fk('latest_indexcard_rdf')
@linked_fk('source_record_suid')
@linked_many('focustype_identifier_set')
@linked_many('focus_identifier_set')
class IndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'uuid',
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('uuid', 'source_record_suid', 'created', 'modified')
    show_full_result_count = False
    search_fields = ('uuid',)
    list_select_related = ('source_record_suid',)


@admin.register(LatestIndexcardRdf, site=admin_site)
@linked_fk('from_raw_datum')
@linked_fk('indexcard')
class LatestIndexcardRdfAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'turtle_checksum_iri',
        'rdf_as_turtle',
        'focus_iri',
    )
    paginator = TimeLimitedPaginator
    list_display = ('indexcard', 'created', 'modified')
    list_select_related = ('indexcard',)
    show_full_result_count = False


@admin.register(ArchivedIndexcardRdf, site=admin_site)
@linked_fk('from_raw_datum')
@linked_fk('indexcard')
@linked_many('focus_identifier_set')
@linked_many('focustype_identifier_set')
class ArchivedIndexcardRdfAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
        'turtle_checksum_iri',
        'rdf_as_turtle',
        'focus_iri',
    )
    paginator = TimeLimitedPaginator
    list_display = ('id', 'indexcard', 'from_raw_datum', 'created', 'modified')
    list_select_related = ('indexcard', 'from_raw_datum',)
    show_full_result_count = False


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