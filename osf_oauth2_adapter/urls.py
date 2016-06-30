from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from osf_oauth2_adapter.provider import OSFProvider

urlpatterns = default_urlpatterns(OSFProvider)
