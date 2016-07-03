import ast
import importlib

from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from share.models.base import ExtraData
from share.models.celery import CeleryTask
from share.models.change import ChangeSet
from share.models.core import RawData, NormalizedData, ShareUser
from share.models.creative import CreativeWork, Manuscript, Preprint
from share.models.entities import Organization, Institution, Funder
from share.models.meta import Venue, Award, Taxonomy, Tag
from share.models.people import Identifier, Contributor, Email, Person, PersonEmail, Affiliation


class NormalizedDataAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]


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

    def accept_changes(self, request, queryset):
        for changeset in queryset:
            changeset.accept()
    accept_changes.short_description = 'accept changes'

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
admin.site.register(NormalizedData, NormalizedDataAdmin)
admin.site.register(CeleryTask, CeleryTaskAdmin)

admin.site.register(CreativeWork)

admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(ShareUser)
