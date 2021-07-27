from django.urls import re_path as url
from django.views.decorators.csrf import csrf_exempt

from api.search import views


urlpatterns = [
    # only match _count and _search requests
    url(
        r'^(?P<url_bits>(?:\w+/)?_(?:search|count)/?)$',
        csrf_exempt(views.ElasticSearchView.as_view()),
        name='search'
    ),
    # match _suggest requests
    url(
        r'^(?P<url_bits>(?:\w+/)?_(?:suggest)/?)$',
        csrf_exempt(views.ElasticSearchPostOnlyView.as_view()),
        name='search_post'
    ),
    # match _mappings requests
    url(
        r'^(?P<url_bits>_mappings(/.+|$|/))',
        csrf_exempt(views.ElasticSearchGetOnlyView.as_view()),
        name='search_get'
    ),
    # match specific document requests
    url(
        r'^(?P<url_bits>[^_][\w_-]+/[^_][\w_-]+/?$)',
        csrf_exempt(views.ElasticSearchGetOnlyView.as_view()),
        name='search_get'
    ),
    url(
        r'^(?P<url_bits>.*)',
        csrf_exempt(views.ElasticSearch403View.as_view()),
        name='search_403'
    ),
]
