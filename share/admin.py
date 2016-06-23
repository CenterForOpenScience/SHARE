from django.contrib import admin

from .models import Organization, Affiliation, Email, RawData, ShareSource, NormalizedManuscript, ShareUser

# from providers.org.arxiv_api.models import ArxivManuscripts

admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Email)
admin.site.register(RawData)
admin.site.register(ShareSource)
admin.site.register(ShareUser)
admin.site.register(NormalizedManuscript)
# admin.site.register(ArxivManuscripts)
