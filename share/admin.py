import ast
import importlib

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from oauth2_provider.models import AccessToken

from share.models.base import ExtraData
from share.models.celery import CeleryTask
from share.models.change import ChangeSet
from share.models.core import RawData, NormalizedData, ShareUser
from share.models.creative import AbstractCreativeWork
from share.models.entities import Entity
from share.models.meta import Venue, Award, Tag
from share.models.people import Identifier, Contributor, Email, Person, PersonEmail, Affiliation


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
        for changeset in queryset:
            changeset.accept()
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


class CeleryTaskAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('uuid', 'name', 'app_label', 'app_version', 'status', 'started_by')
    actions = ['retry_tasks']
    list_filter = ['status', 'name', 'app_label', 'app_version', 'started_by']

    def retry_tasks(self, request, queryset):
        for changeset in queryset:
            task_id = str(changeset.uuid)
            parts = changeset.name.rpartition('.')
            Task = getattr(importlib.import_module(parts[0]), parts[2])
            args = (changeset.app_label, changeset.started_by.id,) + ast.literal_eval(changeset.args)
            kwargs = ast.literal_eval(changeset.kwargs)
            Task().apply_async(args, kwargs, task_id=task_id)
        pass
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
