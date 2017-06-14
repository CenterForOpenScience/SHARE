from functools import reduce
import operator
import pprint
import uuid

from celery import states

from django.db import models
from django.contrib import admin
from django.utils.html import format_html

from project import celery_app


class TaskNameFilter(admin.SimpleListFilter):
    title = 'Task'
    parameter_name = 'task_name'

    def lookups(self, request, model_admin):
        return sorted((x, x) for x in celery_app.tasks.keys())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(task_name=self.value())
        return queryset


class StatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return sorted((x, x.title()) for x in states.ALL_STATES)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value().upper())
        return queryset


class CeleryTaskResultAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'task_name', 'status_', 'source_config', 'date_modified', 'date_created', 'share_version')
    exclude = ('correlation_id', )
    actions = ('retry', )
    ordering = ('-date_modified', )
    list_filter = (TaskNameFilter, StatusFilter, )
    readonly_fields = (
        'task_id',
        'task_name',
        'task_args', 'task_kwargs',
        'result', 'traceback',
        'meta_',
        'date_created', 'date_modified',
        'share_version'
    )
    show_full_result_count = False
    search_fields = ('task_name', )

    STATUS_COLORS = {
        states.SUCCESS: 'green',
        states.FAILURE: 'red',
        states.STARTED: 'cyan',
        states.RETRY: 'orange',
    }

    def get_search_results(self, request, queryset, search_term):
        try:
            return queryset.filter(task_id=uuid.UUID(search_term)), False
        except ValueError:
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

    def task_args(self, obj):
        return obj.meta['args']

    def task_kwargs(self, obj):
        return pprint.pformat(obj.meta['kwargs'])

    def status_(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: {}">{}</span>',
            self.STATUS_COLORS.get(obj.status, 'black'),
            obj.status.title()
        )
    status_.short_description = 'Status'

    def meta_(self, obj):
        return pprint.pformat(obj.meta)
    status_.short_description = 'Meta'

    def source_config(self, obj):
        return obj.meta.get('source_config')
    source_config.short_description = 'Source Config'

    def retry(self, request, queryset):
        for task in queryset:
            celery_app.tasks[task.task_name].apply_async(
                task.meta.get('args', ()),
                task.meta.get('kwargs', {}),
                task_id=str(task.task_id)
            )
    retry.short_description = 'Retry Tasks'
