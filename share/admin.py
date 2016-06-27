from django.contrib import admin

from share.models.base import ExtraData
from share.models.change import ChangeRequirement
from share.models.contributor import Identifier
from share.models.creative.meta import Venue, Institution, Funder, Award, DataProvider, Taxonomy, Tag
from .models import Organization, Affiliation, Email, RawData, NormalizedManuscript, ShareUser, Normalization, \
    NormalizationQueue, Person, PersonEmail, ChangeRequest, ChangeSet, Preprint, Manuscript, CreativeWork
from share.models.creative.contributors import Contributor


# from providers.org.arxiv_api.models import ArxivManuscripts

class NormalizedManuscriptAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ['source', ]

def count_changes(obj):
    return len(obj.changes)
count_changes.short_description = 'number of changes'

class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('target', count_changes, 'status')
    # list_filter = ['status', ]


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

admin.site.register(ChangeRequirement)
admin.site.register(ChangeRequest, ChangeRequestAdmin)
admin.site.register(ChangeSet)
admin.site.register(ShareUser)
admin.site.register(Normalization)
admin.site.register(NormalizationQueue)
# admin.site.register(ArxivManuscripts)


