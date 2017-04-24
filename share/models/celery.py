from model_utils import Choices

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _
from typedmodels.models import TypedModel

from db.deletion import DATABASE_CASCADE

from share.models.fuzzycount import FuzzyCountManager


class CeleryTask(TypedModel):
    STATUS = Choices(
        (0, 'started', _('started')),
        (1, 'retried', _('retried')),
        (2, 'failed', _('failed')),
        (3, 'succeeded', _('succeeded')),
    )

    uuid = models.UUIDField(db_index=True, unique=True)
    name = models.TextField(blank=True, db_index=True)
    args = models.TextField(blank=True)
    kwargs = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='started_by', null=True, on_delete=DATABASE_CASCADE)
    # TODO rename to 'source'
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='provider', null=True, on_delete=DATABASE_CASCADE)
    status = models.IntegerField(choices=STATUS)

    objects = FuzzyCountManager()

    class Meta:
        ordering = ('-timestamp',)
        index_together = ('type', 'name', 'app_label', 'timestamp')


# TODO rename to get rid of 'Provider'
class CeleryProviderTask(CeleryTask):
    app_label = models.TextField(db_index=True, blank=True)
    app_version = models.TextField(db_index=True, blank=True)
