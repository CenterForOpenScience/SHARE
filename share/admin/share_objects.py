import operator
from functools import reduce

from django.db import models
from django.contrib import admin
from django.core.paginator import Paginator
from django.db import connections
from django.db.models.sql.datastructures import EmptyResultSet
from django.utils.functional import cached_property

from share.models import AbstractCreativeWork
from share.models import Source
from share.util import IDObfuscator


class FuzzyPaginator(Paginator):

    @cached_property
    def count(self):
        cursor = connections[self.object_list.db].cursor()

        try:
            cursor.execute('SELECT count_estimate(%s);', (cursor.mogrify(*self.object_list.query.sql_with_params()).decode(), ))
        except EmptyResultSet:
            return 0

        return int(cursor.fetchone()[0])


class SourcesInline(admin.TabularInline):
    extra = 1
    verbose_name = 'Source'
    verbose_name_plural = 'Sources'
    model = AbstractCreativeWork.sources.through

    def __init__(self, parent_model, admin_site):
        self.model = parent_model.sources.through
        super().__init__(parent_model, admin_site)

    def formfield_for_dbfield(self, db_field, **kwargs):
        ret = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'shareuser':
            ret.widget.can_add_related = False
            ret.widget.can_change_related = False
            ret.widget.can_delete_related = False
        return ret


class TypedModelFilter(admin.SimpleListFilter):
    title = 'Type'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return sorted([
            (k, v._meta.verbose_name_plural.title())
            for k, v
            in model_admin.model._typedmodels_registry.items()
        ])

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(type=self.value())
        return queryset


class SourcesFilter(admin.SimpleListFilter):
    title = 'Source'
    parameter_name = 'source'

    def lookups(self, request, model_admin):
        return sorted([
            (source.user.username, source.long_title)
            for source in Source.objects.select_related('user').all()
        ], key=lambda x: x[1])

    def queryset(self, request, queryset):
        if self.value():
            # Note: If this ever can filter on multiple sources
            # this will require a .distinct()
            return queryset.filter(sources__username=self.value())
        return queryset


class ShareObjectAdmin(admin.ModelAdmin):
    actions = None
    exclude = ('extra', 'same_as', 'change', )
    inlines = (SourcesInline, )
    list_filter = (TypedModelFilter, SourcesFilter, )
    # Django forces order by pk desc which results in a seqscan if we add anything else
    # ordering = ('-date_modified', )
    readonly_fields = ('date_created', 'date_modified', )
    show_full_result_count = False
    paginator = FuzzyPaginator

    def get_search_results(self, request, queryset, search_term):
        ret = super().get_search_results(request, queryset, search_term)
        return ret

    def get_type(self, obj):
        return obj._meta.verbose_name_plural.title()

    def encoded_id(self, obj):
        return IDObfuscator.encode(obj)

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False

    def save_model(self, request, obj, form, change):
        if form.changed_data:
            obj.administrative_change(**{
                key: form.cleaned_data[key]
                for key in form.changed_data
            })

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if form.changed_data:
            # If we've already been changed there's nothing to worry about
            return

        # If a m 2 m has changed, force date_modified to update so this
        # object get re-indexed
        for fs in formsets:
            if fs.has_changed():
                form.instance.administrative_change(allow_empty=True)
                break


class CreativeWorkAdmin(ShareObjectAdmin):
    list_display = ('encoded_id', 'id', 'get_type', 'title', 'date_modified', 'date_created', )
    search_fields = ('identifiers__uri', )
    show_change_link = False

    def get_search_results(self, request, queryset, search_term):
        # Overriden because there is no way to opt out of a case insensitive search
        search_fields = self.get_search_fields(request)
        use_distinct = bool(search_term)
        if search_fields and search_term:
            orm_lookups = ['{}__startswith'.format(search_field) for search_field in search_fields]
            for bit in search_term.split():
                or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                queryset = queryset.filter(reduce(operator.or_, or_queries))

        return queryset, use_distinct
