from django.utils.functional import cached_property

from share.provider import ProviderAppConfig
from .harvester import OSFRegistrationsHarvester


class AppConfig(ProviderAppConfig):
    name = 'providers.io.osf.registrations'
    version = '0.0.1'
    title = 'osf_registrations'
    long_title = 'Open Science Framework Registrations'
    home_page = 'http://api.osf.io/registrations/'
    harvester = OSFRegistrationsHarvester

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.io.osf')
