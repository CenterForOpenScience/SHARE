from django.utils.functional import cached_property

from share.normalize.soup import SoupXMLNormalizer
from share.provider import ProviderAppConfig

from .harvester import PeerJPreprintHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.peerj.preprints'
    version = '0.0.1'
    title = 'peerj'
    long_title = 'PeerJ'
    home_page = 'https://peerj.com/articles/'
    harvester = PeerJPreprintHarvester
    normalizer = SoupXMLNormalizer

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.com.peerj')
