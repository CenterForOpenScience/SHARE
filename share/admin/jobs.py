from furl import furl
from prettyjson import PrettyJSONWidget

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from share.admin.util import FuzzyPaginator, linked_fk, SourceConfigFilter
from share.models.fields import DateTimeAwareJSONField
from share.models.jobs import AbstractBaseJob


STATUS_COLORS = {
    AbstractBaseJob.STATUS.created: 'blue',
    AbstractBaseJob.STATUS.started: 'cyan',
    AbstractBaseJob.STATUS.failed: 'red',
    AbstractBaseJob.STATUS.succeeded: 'green',
    AbstractBaseJob.STATUS.rescheduled: 'goldenrod',
    AbstractBaseJob.STATUS.forced: 'maroon',
    AbstractBaseJob.STATUS.skipped: 'orange',
    AbstractBaseJob.STATUS.retried: 'darkseagreen',
    AbstractBaseJob.STATUS.cancelled: 'grey',
}


def readonly_link(obj, display_str=None):
    url = reverse('admin:{}_{}_change'.format(obj._meta.app_label, obj._meta.model_name), args=[obj.id])
    return format_html('<a href="{}">{}</a>', url, display_str or str(obj))


@linked_fk('source_config')
class BaseJobAdmin(admin.ModelAdmin):
    list_filter = ('status', SourceConfigFilter, )
    list_select_related = ('source_config', )
    actions = ('restart_tasks', )
    readonly_fields = ('task_id', 'error_type', 'error_message', 'error_context', 'completions', 'date_started', 'source_config_version', )
    show_full_result_count = False
    paginator = FuzzyPaginator

    def status_(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: {}">{}</span>',
            STATUS_COLORS[obj.status],
            AbstractBaseJob.STATUS[obj.status].title(),
        )

    def restart_tasks(self, request, queryset):
        queryset.update(status=AbstractBaseJob.STATUS.created)
    restart_tasks.short_description = 'Re-enqueue'


class HarvestJobAdmin(BaseJobAdmin):
    list_display = ('id', 'source_config', 'status_', 'start_date_', 'end_date_', 'share_version', 'harvest_job_actions', )
    readonly_fields = BaseJobAdmin.readonly_fields + ('harvester_version', 'start_date', 'end_date', 'harvest_job_actions',)

    def start_date_(self, obj):
        return obj.start_date.isoformat()

    def end_date_(self, obj):
        return obj.end_date.isoformat()

    def harvest_job_actions(self, obj):
        url = furl(reverse('admin:source-config-harvest', args=[obj.source_config_id]))
        url.args['start'] = self.start_date_(obj)
        url.args['end'] = self.end_date_(obj)
        url.args['superfluous'] = True
        return format_html('<a class="button" href="{}">Restart</a>', url.url)
    harvest_job_actions.short_description = 'Actions'


@linked_fk('suid')
@linked_fk('raw')
class IngestJobAdmin(BaseJobAdmin):
    list_display = ('id', 'source_config', 'suid', 'status_', 'date_started', 'share_version', )
    list_select_related = BaseJobAdmin.list_select_related + ('suid',)
    readonly_fields = BaseJobAdmin.readonly_fields + ('transformer_version', 'regulator_version', 'ingested_normalized_data', 'retries')
    fake_readonly_fields = ('transformed_datum', 'regulated_datum')
    formfield_overrides = {
        DateTimeAwareJSONField: {
            'widget': PrettyJSONWidget(attrs={
                'initial': 'parsed',
                'cols': 120,
                'rows': 20
            })
        }
    }

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        for field_name in self.fake_readonly_fields:
            form.base_fields[field_name].disabled = True
        return form
