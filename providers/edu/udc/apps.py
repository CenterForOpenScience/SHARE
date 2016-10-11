from django.utils.functional import cached_property

from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.edu.udc'
    version = '0.0.1'
    title = 'udc'
    long_title = 'University of Minnesota, Digital Conservancy'
    home_page = 'http://conservancy.umn.edu/'
    url = 'http://conservancy.umn.edu/oai/request'
    approved_sets = ['com_11299_45272', 'com_11299_169792', 'com_11299_166578']

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.gov.pubmedcentral')
