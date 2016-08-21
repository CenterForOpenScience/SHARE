from django.utils.functional import cached_property

from share.provider import OAIProviderAppConfig


class AppConfig(OAIProviderAppConfig):
    name = 'providers.org.datacite.oai'
    version = '0.0.1'
    title = 'datacite'
    long_title = 'DataCite MDS'
    home_page = 'http://oai.datacite.org/'
    url = 'http://oai.datacite.org/oai'
    disabled = True

    @cached_property
    def user(self):
        from share.models import ShareUser
        return ShareUser.objects.get(robot='providers.org.datacite')
