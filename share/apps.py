from django.apps import AppConfig
from model_utils import Choices
from django.utils.translation import ugettext as _


class ShareConfig(AppConfig):
    name = 'share'
    link_type_choices = Choices(
        ('doi', _('DOI')),
        ('orcid', _('Orchid')),
        ('provider', _('Provider')),
        ('misc', _('Miscellaneous')),
    )
