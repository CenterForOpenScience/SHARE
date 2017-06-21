from django.contrib import admin
from django.utils.html import format_html

from share.admin.util import FuzzyPaginator
from share.models.ingest import SourceConfig
from share.models.jobs import AbstractBaseJob, HarvestJob, IngestJob


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


class SourceConfigFilter(admin.SimpleListFilter):
    title = 'Source Config'
    parameter_name = 'source_config'

    def lookups(self, request, model_admin):
        # TODO make this into a cool hierarchy deal
        # return SourceConfig.objects.select_related('source').values_list('
        return SourceConfig.objects.order_by('label').values_list('id', 'label')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_config=self.value())


class BaseJobAdmin(admin.ModelAdmin):
    list_filter = ('status', SourceConfigFilter, )
    list_select_related = ('source_config__source', )
    actions = ('restart_tasks', )
    readonly_fields = ('task_id', 'context', 'completions', 'date_started', 'source_config_version', )
    show_full_result_count = False
    paginator = FuzzyPaginator

    def source_config_(self, obj):
        return obj.source_config.label

    def status_(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: {}">{}</span>',
            STATUS_COLORS[obj.status],
            HarvestJob.STATUS[obj.status].title(),
        )

    def restart_tasks(self, request, queryset):
        queryset.update(status=HarvestJob.STATUS.created)
    restart_tasks.short_description = 'Re-enqueue'


class HarvestJobAdmin(BaseJobAdmin):
    list_display = ('id', 'source_config_', 'share_version', 'status_', 'start_date_', 'end_date_', 'harvest_job_actions', )
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


class IngestJobAdmin(BaseJobAdmin):
    list_display = ('id', 'suid', 'source_config_', 'share_version', 'status_', )
    list_select_related = BaseJobAdmin.list_select_related + ('suid',)
    readonly_fields = BaseJobAdmin.readonly_fields + ('suid', 'transformed_data', 'regulated_data', 'raw', 'transformer_version', 'regulator_version', )
