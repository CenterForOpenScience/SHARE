from model_utils import Choices

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _

from db.deletion import DATABASE_CASCADE


class SiteBanner(models.Model):
    COLOR = Choices(
        (0, 'success', _('success')),
        (1, 'info', _('info')),
        (2, 'warning', _('warning')),
        (3, 'danger', _('danger'))
    )

    active = models.BooleanField(default=True, db_index=True)

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    color = models.IntegerField(choices=COLOR, default=COLOR.info)
    icon = models.CharField(blank=True, max_length=31, default='exclamation')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=DATABASE_CASCADE)
    last_modified_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=DATABASE_CASCADE)
