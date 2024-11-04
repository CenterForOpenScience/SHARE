from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView, OAuth2CallbackView
from django.views.generic.base import TemplateView

from .adapters import OSFOAuth2Adapter


class LoginErroredCancelledView(TemplateView):
    template_name = ("allauth/login_errored_cancelled.html")


login_errored_cancelled = LoginErroredCancelledView.as_view()

# used by allauth.socialaccount.providers.oauth2.urls.default_urlpatterns
oauth2_login = OAuth2LoginView.adapter_view(OSFOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(OSFOAuth2Adapter)
