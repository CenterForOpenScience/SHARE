from django.contrib.admin import SimpleListFilter
from django.core.paginator import Paginator
from django.db import connections
from django.db.models.sql.datastructures import EmptyResultSet
from django.utils.functional import cached_property
from django.urls import reverse
from django.utils.html import format_html

from share.models import SourceConfig


class FuzzyPaginator(Paginator):

    @cached_property
    def count(self):
        cursor = connections[self.object_list.db].cursor()

        try:
            cursor.execute('SELECT count_estimate(%s);', (cursor.mogrify(*self.object_list.query.sql_with_params()).decode(), ))
        except EmptyResultSet:
            return 0

        return int(cursor.fetchone()[0])


def append_to_cls_property(cls, property_name, value):
    old_values = getattr(cls, property_name, None) or []
    setattr(cls, property_name, tuple([*old_values, value]))


def linked_fk(field_name):
    """Decorator that adds a link for a foreign key field
    """
    def add_link(cls):
        def link(self, instance):
            linked_obj = getattr(instance, field_name)
            url = reverse(
                'admin:{}_{}_change'.format(
                    linked_obj._meta.app_label,
                    linked_obj._meta.model_name,
                ),
                args=[linked_obj.id]
            )
            return format_html('<a href="{}">{}</a>', url, repr(linked_obj))
        link_field = '{}_link'.format(field_name)
        link.short_description = field_name.replace('_', ' ')
        setattr(cls, link_field, link)
        append_to_cls_property(cls, 'readonly_fields', link_field)
        append_to_cls_property(cls, 'exclude', field_name)
        return cls
    return add_link


class SourceConfigFilter(SimpleListFilter):
    title = 'Source Config'
    parameter_name = 'source_config'

    def lookups(self, request, model_admin):
        return SourceConfig.objects.order_by('label').values_list('id', 'label')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_config=self.value())
