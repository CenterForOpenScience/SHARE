from django.contrib import admin

from .models import Contributor, Organization, Affiliation, Email, Manuscript
from providers.org_arxiv_api.models import ArxivManuscripts

admin.site.register(Contributor)
admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Email)
admin.site.register(Manuscript)
admin.site.register(ArxivManuscripts)

