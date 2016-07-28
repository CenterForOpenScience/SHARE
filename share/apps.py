from django.apps import AppConfig
from model_utils import Choices
from django.utils.translation import ugettext as _


class ShareConfig(AppConfig):
    name = 'share'
    link_type_choices = Choices(
        ('doi', _('DOI')),
        ('provider', _('Provider')),
        ('misc', _('Miscellaneous')),
        ('eissn', _('Electronic International Standard Serial Number')),
        ('ark', _('ARK')),
        ('arxiv', _('arXiv')),
        ('bibcode', _('bibcode')),
        ('doi', _('DOI')),
        ('ean13', _('EAN13')),
        ('eissn', _('EISSN')),
        ('handle', _('Handle')),
        ('isbn', _('ISBN')),
        ('issn', _('ISSN')),
        ('istc', _('ISTC')),
        ('lissn', _('LISSN')),
        ('lsid', _('LSID')),
        ('pmid', _('PMID')),
        ('purl', _('PURL')),
        ('upc', _('UPC')),
        ('url', _('URL')),
        ('urn', _('URN'))
    )
