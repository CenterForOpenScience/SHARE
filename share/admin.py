from django.contrib import admin

from .models import Contributor, Organization, Affiliation, Email

admin.site.register(Contributor)
admin.site.register(Organization)
admin.site.register(Affiliation)
admin.site.register(Email)