from .apps import OsfOauth2AdapterConfig
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class OSFAccount(ProviderAccount):
    def to_str(self):
        # default ... reserved word?
        dflt = super(OSFAccount, self).to_str()
        return next(
            value
            for value in (
                # try the name first, then the id, then the super value
                '{} {}'.format(
                    self.account.extra_data.get('first_name', None),
                    self.account.extra_data.get('last_name', None)
                ),
                self.account.extra_data.get('id', None),
                dflt
            )
            if value is not None
        )


class OSFProvider(OAuth2Provider):
    id = 'osf'
    name = 'Open Science Framework'
    account_class = OSFAccount

    def extract_common_fields(self, data):
        attributes = data.get('data').get('attributes')
        return dict(
            # we could put more fields here later
            # the api has much more available, just not sure how much we need right now
            username=data.get('data').get('id'),
            first_name=attributes.get('given_name', None),
            last_name=attributes.get('family_name', None),
            time_zone=attributes.get('timezone', None),
            locale=attributes.get('locale', None),
            profile_image_url=data.get('data').get('links').get('profile_image')
        )

    def extract_uid(self, data):
        return str(data.get('data').get('id'))

    def get_default_scope(self):
        return OsfOauth2AdapterConfig.default_scopes


provider_classes = [OSFProvider]
