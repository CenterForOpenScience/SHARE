from django.contrib import admin

from share.models.base import ExtraData
from share.models.people import Identifier
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Taxonomy, Tag
from .models import Organization, Affiliation, Email, RawData, NormalizedManuscript, ShareUser, \
    Person, PersonEmail, ChangeSet, Preprint, Manuscript, CreativeWork, CeleryEvent, CeleryTask
from share.models.creative.contributors import Contributor

class ShareAdminSite(admin.AdminSite):
    site_header = 'SHARE Administration'
    site_title = 'SHARE Administration'
    empty_value_display = '-- INTENTIONALLY LEFT BLANK --'


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
    # list_display = ['']
    pass

class CeleryEventAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'type', ]
    list_filter = ['type']

share_admin = ShareAdminSite(name='share_admin')

share_admin.register(Organization)
share_admin.register(Affiliation)
share_admin.register(Person, PersonAdmin)
share_admin.register(PersonEmail)
share_admin.register(Identifier)
share_admin.register(Venue)
share_admin.register(Institution)
share_admin.register(Funder)
share_admin.register(Award)
share_admin.register(DataProvider)
share_admin.register(Taxonomy)
share_admin.register(Tag)
share_admin.register(ExtraData)
share_admin.register(Contributor)
share_admin.register(Email)
share_admin.register(RawData)
share_admin.register(Preprint)
share_admin.register(Manuscript)
share_admin.register(NormalizedManuscript, NormalizedManuscriptAdmin)
share_admin.register(CeleryEvent, CeleryEventAdmin)
share_admin.register(CeleryTask, CeleryTaskAdmin)

share_admin.register(CreativeWork)

share_admin.register(ChangeSet, ChangeSetAdmin)
share_admin.register(ShareUser)
