from django.conf.urls import include
from django.conf.urls import url

from graphene_django.views import GraphQLView

from api import views


app_name = 'api'

urlpatterns = [
    url('^', include('api.banners.urls')),
    url('^', include('api.normalizeddata.urls')),
    url('^', include('api.rawdata.urls')),
    url('^', include('api.shareobjects.urls')),
    url('^', include('api.sourceregistrations.urls')),
    url('^', include('api.sources.urls')),
    url('^', include('api.users.urls')),

    url('^schemas?/', include('api.schemas.urls')),
    url('^search/', include('api.search.urls')),

    # TODO refactor non-viewset endpoints to conform to new structure
    url(r'status/?', views.ServerStatusView.as_view(), name='status'),
    url(r'rss/?', views.CreativeWorksRSS(), name='rss'),
    url(r'atom/?', views.CreativeWorksAtom(), name='atom'),
    url(r'graph/?', GraphQLView.as_view(graphiql=True)),
]
