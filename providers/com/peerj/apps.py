from share.provider import ProviderAppConfig
from .harvester import PeerJHarvester
from .normalizer import PeerJNormalizer


class AppConfig(ProviderAppConfig):
    name = 'providers.com.peerj'
    version = '0.0.1'
    title = 'peerj'
    long_title = 'PeerJ'
    home_page = 'https://peerj.com/articles/'
    harvester = PeerJHarvester
    normalizer = PeerJNormalizer
