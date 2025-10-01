from django.urls import path, re_path

from .views.browse import BrowseIriView
from .views.docs import (
    OpenapiHtmlView,
    OpenapiJsonView,
)
from .views.feeds import (
    CardsearchRssView,
    CardsearchAtomView,
)
from .views.ingest import RdfIngestView
from .views.indexcard import IndexcardView
from .views.search import (
    CardsearchView,
    ValuesearchView,
)


app_name = 'trove'

urlpatterns = [
    path('index-card/<uuid:indexcard_uuid>', view=IndexcardView.as_view(), name='index-card'),
    path('index-card-search', view=CardsearchView.as_view(), name='index-card-search'),
    path('index-value-search', view=ValuesearchView.as_view(), name='index-value-search'),
    path('index-card-search/rss.xml', view=CardsearchRssView.as_view(), name='cardsearch-rss'),
    path('index-card-search/atom.xml', view=CardsearchAtomView.as_view(), name='cardsearch-atom'),
    path('browse', view=BrowseIriView.as_view(), name='browse-iri'),
    path('ingest', view=RdfIngestView.as_view(), name='ingest-rdf'),
    path('docs/openapi.json', view=OpenapiJsonView.as_view(), name='docs.openapi-json'),
    path('docs/openapi.html', view=OpenapiHtmlView.as_view(), name='docs.openapi-html'),
    re_path(r'docs/?', view=OpenapiHtmlView.as_view(), name='docs'),
]
