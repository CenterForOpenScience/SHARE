from model_utils import Choices

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _


class ProviderRegistration(models.Model):

    STATUS = Choices(
        (0, 'pending', _('pending')),
        (1, 'accepted', _('accepted')),
        (2, 'implemented', _('implemented')),
        (3, 'rejected', _('rejected'))
    )

    status = models.IntegerField(choices=STATUS, default=STATUS.pending)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    contact_name = models.TextField(max_length=300)
    contact_email = models.EmailField()
    contact_affiliation = models.TextField(max_length=300)

    direct_source = models.BooleanField(default=False)

    source_name = models.TextField(max_length=300)
    source_description = models.TextField(max_length=1000)
    source_rate_limit = models.TextField(blank=True, default='', max_length=300)
    source_documentation = models.TextField(blank=True, default='', max_length=300)
    source_preferred_metadata_prefix = models.TextField(blank=True, default='', max_length=300)
    source_oai = models.BooleanField(default=False)
    source_base_url = models.URLField(blank=True, default='')
    source_disallowed_sets = models.TextField(blank=True, default='', max_length=300)
    source_additional_info = models.TextField(blank=True, default='', max_length=1000)

    class Meta:
        ordering = ['-submitted_at']
