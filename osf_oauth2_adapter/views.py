import requests
from .apps import OsfOauth2AdapterConfig
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter, OAuth2LoginView, OAuth2CallbackView

from osf_oauth2_adapter.provider import OSFProvider


class OSFOAuth2Adapter(OAuth2Adapter):
    provider_id = OSFProvider.id
    base_url = '{}oauth2/{}'.format(OsfOauth2AdapterConfig.osf_accounts_url, '{}')
    access_token_url = base_url.format('token')
    authorize_url = base_url.format('authorize')
    profile_url = base_url.format('profile')

    def complete_login(self, request, app, access_token, **kwargs):
        extra_data = requests.get(self.profile_url, params={
            'access_token': access_token.token
        })

        return self.get_provider().sociallogin_from_response(
            request,
            extra_data.json()
        )

oauth2_login = OAuth2LoginView.adapter_view(OSFOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(OSFOAuth2Adapter)
