from django.utils.functional import cached_property

from share.provider import ProviderAppConfig
from .harvester import ZenodoHarvester
from providers.org.datacite.normalizer import DataciteNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.org.zenodo.datacite'
    version = '0.0.1'
    title = 'zenodo'
    long_title = 'Zenodo'
    home_page = 'https://zenodo.org/oai2d'
    url = 'https://zenodo.org/oai2d'
    harvester = ZenodoHarvester
    normalizer = DataciteNormalizer
    rate_limit = (1, 3)
    namespaces = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://datacite.org/schema/kernel-3': None,
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://schema.datacite.org/oai/oai-1.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
    }

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.org.zenodo')
