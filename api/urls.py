from django.urls import include, re_path as url

from api import views
from api.base.views import RootView


app_name = 'api'

urlpatterns = [
    url('^$', RootView.as_view()),
    url('^', include('api.banners.urls')),
    url('^', include('api.rawdata.urls')),
    url('^', include('api.sourceconfigs.urls')),
    url('^', include('api.sources.urls')),
    url('^', include('api.suids.urls')),
    url('^', include('api.users.urls')),

    url('^search/', include('api.search.urls'), name='search'),
    url(r'^status/?', views.ServerStatusView.as_view(), name='status'),
    url(r'^feeds/rss/?', views.MetadataRecordsRSS(), name='feeds.rss'),
    url(r'^feeds/atom/?', views.MetadataRecordsAtom(), name='feeds.atom'),
]
