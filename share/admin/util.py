from django.contrib.admin import SimpleListFilter
from django.core.paginator import Paginator
from django.db import connection, transaction, OperationalError
from django.utils.functional import cached_property
from django.urls import reverse
from django.utils.html import format_html

from share.models import SourceConfig


# TimeLimitedPaginator from https://hakibenita.com/optimizing-the-django-admin-paginator
class TimeLimitedPaginator(Paginator):
    """
    Paginator that enforces a timeout on the count operation.
    If the count times out, a bogus large value is returned instead.
    """
    @cached_property
    def count(self):
        # We set the timeout in a db transaction to prevent it from
        # affecting other transactions.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SET LOCAL statement_timeout TO 500;')
            try:
                return super().count
            except OperationalError:
                return 999999999999


def append_to_cls_property(cls, property_name, value):
    old_values = getattr(cls, property_name, None) or []
    setattr(cls, property_name, tuple([*old_values, value]))


def admin_link(linked_obj):
    url = reverse(
        'admin:{}_{}_change'.format(
            linked_obj._meta.app_label,
            linked_obj._meta.model_name,
        ),
        args=[linked_obj.id]
    )
    return format_html('<a href="{}">{}</a>', url, repr(linked_obj))


def linked_fk(field_name):
    """Decorator that adds a link for a foreign key field
    """
    def add_link(cls):
        def link(self, instance):
            linked_obj = getattr(instance, field_name)
            return admin_link(linked_obj)
        link_field = '{}_link'.format(field_name)
        link.short_description = field_name.replace('_', ' ')
        setattr(cls, link_field, link)
        append_to_cls_property(cls, 'readonly_fields', link_field)
        append_to_cls_property(cls, 'exclude', field_name)
        return cls
    return add_link


def linked_many(field_name, order_by=None, select_related=None):
    """Decorator that adds links for a *-to-many field
    """
    def add_links(cls):
        def links(self, instance):
            linked_qs = getattr(instance, field_name).all()
            if select_related:
                linked_qs = linked_qs.select_related(*select_related)
            if order_by:
                linked_qs = linked_qs.order_by(*order_by)
            return format_html(
                '<ol>{}</ol>',
                format_html(''.join(
                    '<li>{}</li>'.format(admin_link(obj))
                    for obj in linked_qs
                ))
            )
        links_field = '{}_links'.format(field_name)
        links.short_description = field_name.replace('_', ' ')
        setattr(cls, links_field, links)
        append_to_cls_property(cls, 'readonly_fields', links_field)
        append_to_cls_property(cls, 'exclude', field_name)
        return cls
    return add_links


class SourceConfigFilter(SimpleListFilter):
    title = 'Source Config'
    parameter_name = 'source_config'

    def lookups(self, request, model_admin):
        return SourceConfig.objects.order_by('label').values_list('id', 'label')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_config=self.value())
