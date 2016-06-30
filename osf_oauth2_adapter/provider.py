from django.conf import settings
import requests
from requests.packages.urllib3.exceptions import HTTPError
from .apps import OsfOauth2AdapterConfig
from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
import logging

logger = logging.getLogger(__name__)


class OSFAccount(ProviderAccount):
    def to_str(self):
        dflt = super(OSFAccount, self).to_str()
        return next(
            value
            for value in (
                self.account.extra_data.get('name', None),
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
        user_id = data.get('id')
        scopes = data.get('scopes')

        resp = requests.get('{}v2/users/{}/'.format(OsfOauth2AdapterConfig.osf_api_url, user_id))
        try:
            resp.raise_for_status()
        except HTTPError as ex:
            # TODO: There might be a better way to handle this.
            # This just seemed like the safest way to not allow people an account if their
            # profile request fails.
            logger.exception('Caught a V2 HTTPError during user profile request')
            raise ex
        else:
            # json-api ftw
            user_info = resp.json().get('data').get('attributes')
            import ipdb
            ipdb.set_trace()
            return dict(
                username=data.get('id'),
                first_name=user_info.get('given_name'),
                last_name=user_info.get('family_name'),
            )

    def extract_uid(self, data):
        return str(data['id'])

    def get_default_scope(self):
        return OsfOauth2AdapterConfig.default_scopes

providers.registry.register(OSFProvider)
