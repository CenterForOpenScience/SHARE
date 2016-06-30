from django.contrib import admin

from share.models.base import ExtraData
from share.models.people import Identifier
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Taxonomy, Tag
from .models import Organization, Affiliation, Email, RawData, NormalizedManuscript, ShareUser, Normalization, \
    NormalizationQueue, Person, PersonEmail, Change, ChangeSet, Preprint, Manuscript, CreativeWork
from share.models.creative.contributors import Contributor


class NormalizedManuscriptAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]


def count_changes(obj):
    return len(obj.change)
count_changes.short_description = 'number of changes'


# class ChangeAdmin(admin.ModelAdmin):
#     list_display = ('target', count_changes, 'status')
    # list_filter = ['status', ]


def accept_changes(self, request, queryset):
    for changeset in queryset:
        changeset.accept()

accept_changes.short_description = 'Accept changes'


# class ChangeSetAdmin(admin.ModelAdmin):
#     actions = [accept_changes]



admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Person)
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

# admin.site.register(Change, ChangeAdmin)
# admin.site.register(ChangeSet, ChangeSetAdmin)
admin.site.register(ShareUser)
admin.site.register(Normalization)
admin.site.register(NormalizationQueue)
