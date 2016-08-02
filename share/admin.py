import ast
import importlib

import celery

from django.apps import apps
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from oauth2_provider.models import AccessToken
from django.contrib import messages
from django.contrib.admin.views.main import ChangeList

from share.robot import RobotAppConfig
from share.models.base import ExtraData
from share.models.celery import CeleryTask
from share.models.change import ChangeSet
from share.models.core import RawData, NormalizedData, ShareUser
from share.models.creative import AbstractCreativeWork
from share.models.entities import Entity
from share.models.meta import Venue, Award, Tag, Link
from share.models.people import Identifier, Contributor, Email, Person, PersonEmail, Affiliation
from share.tasks import ApplyChangeSets


class NormalizedDataAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]
    raw_id_fields = ('raw', 'tasks',)


class ChangeSetSubmittedByFilter(SimpleListFilter):
    title = 'Source'
    parameter_name = 'source_id'

    def lookups(self, request, model_admin):
        return ShareUser.objects.filter(is_active=True).values_list('id', 'username')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(normalized_data__source_id=self.value())
        return queryset


class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ('status_', 'count_changes', 'submitted_by', 'submitted_at')
    actions = ['accept_changes']
    list_filter = ['status', ChangeSetSubmittedByFilter]
    raw_id_fields = ('normalized_data',)

    def accept_changes(self, request, queryset):
        ApplyChangeSets().apply_async(kwargs=dict(changeset_ids=[x[0] for x in queryset.values_list('id')], started_by_id=request.user.id))
        messages.success(request, 'Scheduled {} changesets for acceptance.'.format(queryset.count()))
    accept_changes.short_description = 'Accept changes'

    def submitted_by(self, obj):
        return obj.normalized_data.source
    submitted_by.short_description = 'submitted by'

    def count_changes(self, obj):
        return obj.changes.count()
    count_changes.short_description = 'number of changes'

    def status_(self, obj):
        return ChangeSet.STATUS[obj.status].title()


class PersonAdmin(admin.ModelAdmin):
    list_display = ('pk', 'given_name', 'family_name', 'works')
    raw_id_fields = ('change', 'extra', 'extra_version', 'same_as', 'same_as_version',)

    def works(self, obj):
        return obj.contributor_set.count()


class AppLabelFilter(admin.SimpleListFilter):
    title = 'App Label'
    parameter_name = 'app_label'

    def lookups(self, request, model_admin):
        return sorted([
            (config.label, config.label)
            for config in apps.get_app_configs()
            if isinstance(config, RobotAppConfig)
        ])

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(app_label=self.value())
        return queryset


class TaskNameFilter(admin.SimpleListFilter):
    title = 'Task'
    parameter_name = 'task'

    def lookups(self, request, model_admin):
        return sorted(
            (key, key)
            for key in celery.current_app.tasks.keys()
            if key.startswith('share.')
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(name=self.value())
        return queryset


class CeleryTaskChangeList(ChangeList):
    def get_ordering(self, request, queryset):
        return ['-timestamp']
        return 'timestamp', 'desc'


class CeleryTaskAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'name', 'app_label', 'status', 'started_by')
    actions = ['retry_tasks']
    list_filter = ['status', TaskNameFilter, AppLabelFilter, 'started_by']
    list_select_related = ('provider', 'started_by')
    fields = (
        ('app_label', 'app_version'),
        ('uuid', 'name'),
        ('args', 'kwargs'),
        'timestamp',
        'traceback'
    )
    readonly_fields = ('name', 'uuid', 'args', 'kwargs', 'status', 'app_version', 'app_label', 'timestamp', 'traceback')

    def traceback(self, task):
        return apps.get_model('djcelery', 'taskmeta').objects.filter(task_id=task.uuid).first().traceback

    def get_changelist(self, request, **kwargs):
        return CeleryTaskChangeList

    def retry_tasks(self, request, queryset):
        for changeset in queryset:
            task_id = str(changeset.uuid)
            parts = changeset.name.rpartition('.')
            Task = getattr(importlib.import_module(parts[0]), parts[2])
            args = (changeset.app_label, changeset.started_by.id,) + ast.literal_eval(changeset.args)
            kwargs = ast.literal_eval(changeset.kwargs)
            Task().apply_async(args, kwargs, task_id=task_id)
    retry_tasks.short_description = 'Retry tasks'


class AbstractCreativeWorkAdmin(admin.ModelAdmin):
    list_display = ('type', 'title', 'num_contributors')
    list_filter = ['type']
    raw_id_fields = ('change', 'extra', 'extra_version', 'same_as', 'same_as_version', 'subject', 'subject_version')

    def num_contributors(self, obj):
        return obj.contributors.count()
    num_contributors.short_description = 'Contributors'


class EntityAdmin(admin.ModelAdmin):
    list_display = ('type', 'name')
    list_filter = ('type',)
    raw_id_fields = ('change', 'extra', 'extra_version', 'same_as', 'same_as_version',)


class ContributorAdmin(admin.ModelAdmin):
    raw_id_fields = ('change', 'extra', 'extra_version', 'creative_work', 'creative_work_version', 'same_as', 'same_as_version', 'person', 'person_version',)


class TagAdmin(admin.ModelAdmin):
    raw_id_fields = ('change', 'extra', 'extra_version', 'same_as', 'same_as_version',)


class LinkAdmin(admin.ModelAdmin):
    raw_id_fields = ('change', 'same_as', 'same_as_version', 'extra', 'extra_version',)


class RawDataAdmin(admin.ModelAdmin):
    raw_id_fields = ('tasks',)


class AccessTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'scope')


admin.site.unregister(AccessToken)
admin.site.register(AccessToken, AccessTokenAdmin)

admin.site.register(Affiliation)
admin.site.register(Person, PersonAdmin)
admin.site.register(PersonEmail)
admin.site.register(Identifier)
admin.site.register(Venue)
admin.site.register(Award)
admin.site.register(Link, LinkAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ExtraData)
admin.site.register(Contributor, ContributorAdmin)
admin.site.register(Email)
admin.site.register(RawData, RawDataAdmin)
admin.site.register(NormalizedData, NormalizedDataAdmin)
admin.site.register(CeleryTask, CeleryTaskAdmin)

admin.site.register(Entity, EntityAdmin)
admin.site.register(AbstractCreativeWork, AbstractCreativeWorkAdmin)

admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(ShareUser)
