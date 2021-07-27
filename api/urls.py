from django.urls import include, re_path as url

from api import views
from api.base.views import RootView


app_name = 'api'

urlpatterns = [
    url('^$', RootView.as_view()),
    url('^', include('api.banners.urls')),
    url('^', include('api.formattedmetadatarecords.urls')),
    url('^', include('api.ingestjobs.urls')),
    url('^', include('api.normalizeddata.urls')),
    url('^', include('api.rawdata.urls')),
    url('^', include('api.sourceregistrations.urls')),
    url('^', include('api.sourceconfigs.urls')),
    url('^', include('api.sources.urls')),
    url('^', include('api.suids.urls')),
    url('^', include('api.users.urls')),

    url('^schemas?/', include('api.schemas.urls'), name='schema'),
    url('^search/', include('api.search.urls'), name='search'),

    # TODO refactor non-viewset endpoints to conform to new structure
    url(r'^status/?', views.ServerStatusView.as_view(), name='status'),
    url(r'^rss/?', views.LegacyCreativeWorksRSS(), name='rss'),
    url(r'^atom/?', views.LegacyCreativeWorksAtom(), name='atom'),

    url(r'^feeds/rss/?', views.MetadataRecordsRSS(), name='feeds.rss'),
    url(r'^feeds/atom/?', views.MetadataRecordsAtom(), name='feeds.atom'),
]
