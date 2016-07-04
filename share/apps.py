from django.apps import AppConfig
from model_utils import Choices
from django.utils.translation import ugettext as _


class ShareConfig(AppConfig):
    name = 'share'
    link_type_choices = Choices(
        (0, 'doi', _('DOI')),
        (1, 'orcid', _('Orchid')),
        (2, 'misc', _('Miscellaneous')),
        (3, 'provider', _('Provider')),
    )
