import requests

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter

from .apps import OsfOauth2AdapterConfig


class OSFSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        # super-method populates username, first_name, last_name, email
        user = super().populate_user(request, sociallogin, data)
        user.time_zone = data.get('time_zone')
        user.locale = data.get('locale')
        user.gravatar = data.get('profile_image_url')
        return user


class OSFOAuth2Adapter(OAuth2Adapter):
    provider_id = 'osf'
    base_url = '{}oauth2/{}'.format(OsfOauth2AdapterConfig.osf_accounts_url, '{}')
    access_token_url = base_url.format('token')
    authorize_url = base_url.format('authorize')
    profile_url = '{}v2/users/me/'.format(OsfOauth2AdapterConfig.osf_api_url)

    def complete_login(self, request, app, access_token, **kwargs):
        extra_data = requests.get(self.profile_url, headers={
            'Authorization': 'Bearer {}'.format(access_token.token)
        })
        return self.get_provider().sociallogin_from_response(
            request,
            extra_data.json()
        )
