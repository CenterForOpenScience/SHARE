from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _

from share import util


class SiteBanner(models.Model):
    COLOR_CHOICES = [
        (0, _('success')),
        (1, _('info')),
        (2, _('warning')),
        (3, _('danger'))
    ]
    COLOR = dict(COLOR_CHOICES)

    class JSONAPIMeta(util.BaseJSONAPIMeta):
        pass

    active = models.BooleanField(default=True, db_index=True)

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    color = models.IntegerField(choices=COLOR_CHOICES, default=1)
    icon = models.CharField(blank=True, max_length=31, default='exclamation')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.CASCADE)
    last_modified_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.CASCADE)
