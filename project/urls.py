"""share URL Configuration
"""
from django.urls import include, path, re_path as url
from django.conf import settings
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from revproxy.views import ProxyView

from osf_oauth2_adapter import views as osf_oauth2_adapter_views

from api.views import APIVersionRedirectView, source_icon_view

from share.admin import admin_site
from share.oaipmh.views import OAIPMHView
from share.search import views as search_views

urlpatterns = [
    url(r'^admin/', admin_site.urls),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v3/index-card-search', view=search_views.CardsearchView.as_view(), name='api-index-card-search'),
    path('api/v3/index-property-search', view=search_views.PropertysearchView.as_view(), name='api-index-property-search'),
    path('api/v3/index-value-search', view=search_views.ValuesearchView.as_view(), name='api-index-value-search'),
    path('trove/index-card-search', view=search_views.CardsearchView.as_view(), name='trove-index-card-search'),
    path('trove/index-property-search', view=search_views.PropertysearchView.as_view(), name='trove-index-property-search'),
    path('trove/index-value-search', view=search_views.ValuesearchView.as_view(), name='trove-index-value-search'),
    url(r'^api/v2/', include('api.urls', namespace='api')),
    url(r'^api/(?P<path>(?!v\d+).*)', APIVersionRedirectView.as_view()),
    url(r'^api/v1/', include('api.urls_v1', namespace='api_v1')),
    url(r'^oai-pmh/', OAIPMHView.as_view(), name='oai-pmh'),
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
    urlpatterns += [
        url(r'^(?P<path>{}/.*)$'.format(settings.EMBER_SHARE_PREFIX), ProxyView.as_view(upstream=settings.EMBER_SHARE_URL)),
    ]

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
