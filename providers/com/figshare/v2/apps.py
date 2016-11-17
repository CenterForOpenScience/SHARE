from django.utils.functional import cached_property

from share import ProviderAppConfig
from .harvester import FigshareHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.com.figshare.v2'
    version = '0.0.1'

    title = 'figshare'
    long_title = 'figshare'
    harvester = FigshareHarvester
    home_page = 'https://figshare.com/'

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.com.figshare')
