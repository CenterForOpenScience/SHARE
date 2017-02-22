"""share URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url, include
from django.conf import settings
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from revproxy.views import ProxyView

from osf_oauth2_adapter import views as osf_oauth2_adapter_views

from api.views import APIVersionRedirectView, source_icon_view

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/v2/', include('api.urls', namespace='api')),
    url(r'^api/(?P<path>(?!v\d+).*)', APIVersionRedirectView.as_view()),
    url(r'^api/v1/', include('api.urls_v1', namespace='api_v1')),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^accounts/social/login/cancelled/', osf_oauth2_adapter_views.login_errored_cancelled),
    url(r'^accounts/social/login/error/', osf_oauth2_adapter_views.login_errored_cancelled),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^$', RedirectView.as_view(url='{}/'.format(settings.EMBER_SHARE_PREFIX))),
    url(r'^favicon.ico$', RedirectView.as_view(
        url=staticfiles_storage.url('favicon.ico'),
        permanent=False
    ), name='favicon'),
    url(r'^icons/(?P<source_name>[^/]+).ico$', source_icon_view, name='source_icon'),
]

if settings.DEBUG:
    urlpatterns.extend([
        url(r'^(?P<path>{}/.*)$'.format(settings.EMBER_SHARE_PREFIX), ProxyView.as_view(upstream=settings.EMBER_SHARE_URL))
    ])
