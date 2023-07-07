from django.contrib import admin

from share.admin import admin_site
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many
from trove.models import ResourceIdentifier, RdfIndexcard, DerivedIndexcard


@admin.register(ResourceIdentifier, site=admin_site)
@linked_many('suid_set')
@linked_many('rdf_indexcard_set')
class ResourceIdentifierAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('sufficiently_unique_iri', 'scheme_list', 'created', 'modified')
    show_full_result_count = False
    search_fields = ('sufficiently_unique_iri',)


@admin.register(RdfIndexcard, site=admin_site)
@linked_fk('from_raw_datum')
@linked_many('focus_identifier_set')
@linked_many('focustype_identifier_set')
class RdfIndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('from_raw_datum', 'created', 'modified')
    list_select_related = ('from_raw_datum',)
    show_full_result_count = False


@admin.register(DerivedIndexcard, site=admin_site)
@linked_fk('upriver_card')
@linked_fk('deriver_identifier')
class DerivedIndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('upriver_card', 'deriver_identifier',)
    show_full_result_count = False
