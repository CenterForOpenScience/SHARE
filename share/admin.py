from django.contrib import admin

from share.models.base import ExtraData
from share.models.people import Identifier
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Taxonomy, Tag
from .models import Organization, Affiliation, Email, RawData, NormalizedManuscript, ShareUser, \
    Person, PersonEmail, ChangeSet, Preprint, Manuscript, CreativeWork
from share.models.creative.contributors import Contributor


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


admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Person, PersonAdmin)
admin.site.register(PersonEmail)
admin.site.register(Identifier)
admin.site.register(Venue)
admin.site.register(Institution)
admin.site.register(Funder)
admin.site.register(Award)
admin.site.register(DataProvider)
admin.site.register(Taxonomy)
admin.site.register(Tag)
admin.site.register(ExtraData)
admin.site.register(Contributor)
admin.site.register(Email)
admin.site.register(RawData)
admin.site.register(Preprint)
admin.site.register(Manuscript)
admin.site.register(NormalizedManuscript, NormalizedManuscriptAdmin)

admin.site.register(CreativeWork)

admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(ShareUser)
