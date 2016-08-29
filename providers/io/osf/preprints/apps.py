from django.utils.functional import cached_property

from share.provider import ProviderAppConfig
from .harvester import PreprintHarvester
from .normalizer import PreprintNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.io.osf.preprints'
    version = '0.0.1'
    title = 'osf_preprints'
    long_title = 'OSF'
    emitted_type = 'preprint'
    home_page = 'http://osf.io/api/v2/preprints/'
    harvester = PreprintHarvester
    normalizer = PreprintNormalizer

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.io.osf')
