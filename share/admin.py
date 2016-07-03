import ast
import importlib

from django.contrib import admin

from share.models.base import ExtraData
from share.models.celery import CeleryTask
from share.models.change import ChangeSet
from share.models.core import RawData, NormalizedManuscript, ShareUser
from share.models.creative import CreativeWork, Manuscript, Preprint
from share.models.entities import Organization, Institution, Funder
from share.models.meta import Venue, Award, Taxonomy, Tag
from share.models.people import Identifier, Contributor, Email, Person, PersonEmail, Affiliation


class NormalizedManuscriptAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]


class ChangeSetAdmin(admin.ModelAdmin):
    list_display = ('status_', 'count_changes', 'submitted_by', 'submitted_at')
    actions = ['accept_changes']
    list_filter = ['status', 'submitted_by']

    def accept_changes(self, request, queryset):
        for changeset in queryset:
            changeset.accept()
    accept_changes.short_description = 'Accept changes'

    def count_changes(self, obj):
        return obj.changes.count()
    count_changes.short_description = 'number of changes'

    def status_(self, obj):
        return ChangeSet.STATUS[obj.status].title()


class PersonAdmin(admin.ModelAdmin):
    list_display = ('pk', 'given_name', 'family_name', 'works')

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


admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Person, PersonAdmin)
admin.site.register(PersonEmail)
admin.site.register(Identifier)
admin.site.register(Venue)
admin.site.register(Institution)
admin.site.register(Funder)
admin.site.register(Award)
admin.site.register(Taxonomy)
admin.site.register(Tag)
admin.site.register(ExtraData)
admin.site.register(Contributor)
admin.site.register(Email)
admin.site.register(RawData)
admin.site.register(Preprint)
admin.site.register(Manuscript)
admin.site.register(NormalizedManuscript, NormalizedManuscriptAdmin)
admin.site.register(CeleryTask, CeleryTaskAdmin)

admin.site.register(CreativeWork)

admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(ShareUser)
