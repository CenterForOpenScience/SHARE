import operator
from functools import reduce

from django.conf import settings
from django.db import models
from django.contrib import admin
from django.core.paginator import Paginator
from django.db import connections
from django.db.models.sql.datastructures import EmptyResultSet
from django.forms import ModelChoiceField
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join, mark_safe

from share.admin.util import FuzzyPaginator
from share.models import AbstractCreativeWork
from share.models import Source
from share.models import Subject
from share.util import IDObfuscator
from share.util import InvalidID


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
    # Django forces order by pk desc which results in a seqscan if we add anything else
    # ordering = ('-date_modified', )
    readonly_fields = ('encoded_id', 'date_created', 'date_modified', )
    show_full_result_count = False
    paginator = FuzzyPaginator

    def get_search_results(self, request, queryset, search_term):
        ret = super().get_search_results(request, queryset, search_term)
        return ret

    def get_type(self, obj):
        return obj._meta.verbose_name.title()
    get_type.short_description = 'Type'

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
    list_filter = (TypedModelFilter, SourcesFilter, )
    list_display = ('encoded_id', 'id', 'get_type', 'title', 'date_modified', 'date_created', )
    search_fields = ('identifiers__uri', )
    show_change_link = False

    def get_search_results(self, request, queryset, search_term):
        try:
            return queryset.filter(id=IDObfuscator.decode_id(search_term)), False
        except InvalidID:
            pass

        # Overriden because there is no way to opt out of a case insensitive search
        search_fields = self.get_search_fields(request)
        use_distinct = bool(search_term)
        if search_fields and search_term:
            orm_lookups = ['{}__startswith'.format(search_field) for search_field in search_fields]
            for bit in search_term.split():
                or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                queryset = queryset.filter(reduce(operator.or_, or_queries))

        return queryset, use_distinct


class SubjectChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        return '{}: {}'.format(obj.taxonomy.name, obj.name)


class SubjectAdmin(ShareObjectAdmin):
    search_fields = ('name',)
    readonly_fields = ('taxonomy_link', 'children_links', 'lineage')
    fields = ('lineage', 'children_links', 'name', 'parent', 'taxonomy_link', 'central_synonym', 'is_deleted', 'uri',)
    list_display = ('lineage', 'taxonomy', 'central_synonym', 'is_deleted')
    list_filter = ('taxonomy',)

    def lineage(self, obj):
        return format_html_join(
            ' > ', '<a href="{}">{}</a>',
            ((reverse('admin:share_subject_change', args=(s.id,)), s.name) for s in obj.lineage())
        )

    def taxonomy_link(self, obj):
        taxonomy_url = reverse('admin:share_subjecttaxonomy_change', args=(obj.taxonomy_id,))
        return format_html('<a href="{}">{}</a>', taxonomy_url, obj.taxonomy.name)
    taxonomy_link.short_description = 'Taxonomy'

    def children_links(self, obj):
        items = format_html_join(
            '', '<li style="list-style: square;"><a href="{}">{}</a></li>',
            ((reverse('admin:share_subject_change', args=(child.id,)), child.name) for child in obj.children.order_by('name'))
        )
        return format_html('<ul style="margin-left: 0;">{}</ul>', mark_safe(items))
    children_links.short_description = 'Children'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('taxonomy', 'parent', 'parent__parent',).prefetch_related('children')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        subject_queryset = None
        subject_id = request.resolver_match.args[0]
        if db_field.name == 'parent':
            # Limit to subjects from the same taxonomy
            subject_queryset = Subject.objects.filter(taxonomy__subject__id=subject_id)
        elif db_field.name == 'central_synonym':
            # Limit to subjects from the central taxonomy, or none if this subject is in the central taxonomy
            subject_queryset = Subject.objects.filter(taxonomy__name=settings.SUBJECTS_CENTRAL_TAXONOMY).exclude(taxonomy__subject__id=subject_id)

        if subject_queryset is not None:
            kwargs['queryset'] = subject_queryset.order_by('name').select_related('taxonomy')
            return SubjectChoiceField(required=not db_field.blank, **kwargs)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
