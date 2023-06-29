from django.contrib import admin

from share.admin import admin_site
from share.admin.util import TimeLimitedPaginator, linked_fk, linked_many
from trove.models import PersistentIri, RdfIndexcard, DerivedIndexcard


@admin.register(PersistentIri, site=admin_site)
class PersistentIriAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('schemeless_iri', 'scheme_list', 'created', 'modified')
    show_full_result_count = False
    search_fields = ('schemeless_iri',)


@admin.register(RdfIndexcard, site=admin_site)
@linked_fk('from_raw_datum')
@linked_many('focus_piris')
@linked_many('focustype_piris')
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
@linked_fk('deriver_piri')
class DerivedIndexcardAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created',
        'modified',
    )
    paginator = TimeLimitedPaginator
    list_display = ('upriver_card', 'deriver_piri',)
    show_full_result_count = False
