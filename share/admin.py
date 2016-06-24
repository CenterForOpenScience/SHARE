from django.contrib import admin

from share.models.base import ExtraData
from share.models.change import ChangeRequirement
from .models import Organization, Affiliation, Email, RawData, NormalizedManuscript, ShareUser, Normalization, \
    NormalizationQueue, Person, PersonEmail, ChangeRequest, ChangeSet, Contributor, Preprint, Manuscript, CreativeWork


# from providers.org.arxiv_api.models import ArxivManuscripts

class NormalizedManuscriptAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]

def count_changes(obj):
    return len(obj.changes)
count_changes.short_description = 'number of changes'

class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('target', count_changes, 'status')
    list_filter = ['status', ]


admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Person)
admin.site.register(PersonEmail)
admin.site.register(ExtraData)
admin.site.register(ChangeRequirement)
admin.site.register(ChangeRequest, ChangeRequestAdmin)
admin.site.register(ChangeSet)
admin.site.register(Contributor)
admin.site.register(Preprint)
admin.site.register(Manuscript)
admin.site.register(CreativeWork)
admin.site.register(Email)
admin.site.register(RawData)
admin.site.register(ShareUser)
admin.site.register(Normalization)
admin.site.register(NormalizationQueue)
admin.site.register(NormalizedManuscript, NormalizedManuscriptAdmin)
# admin.site.register(ArxivManuscripts)


