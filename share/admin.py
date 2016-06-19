from django.contrib import admin

from .models import Organization, Affiliation, Email, Manuscript, RawData, ShareSource

# from providers.org.arxiv_api.models import ArxivManuscripts

admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Email)
admin.site.register(Manuscript)
admin.site.register(RawData)
admin.site.register(ShareSource)
# admin.site.register(ArxivManuscripts)
