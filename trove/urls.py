from django.urls import path, re_path
from django.views.generic.base import RedirectView

from .views.browse import BrowseIriView
from .views.ingest import RdfIngestView
from .views.indexcard import IndexcardView
from .views.search import (
    CardsearchView,
    ValuesearchView,
)
from .views.docs import (
    OpenapiHtmlView,
    OpenapiJsonView,
)


app_name = 'trove'

urlpatterns = [
    path('index-card/<uuid:indexcard_uuid>', view=IndexcardView.as_view(), name='index-card'),
    path('index-card-search', view=CardsearchView.as_view(), name='index-card-search'),
    path('index-value-search', view=ValuesearchView.as_view(), name='index-value-search'),
    path('browse', view=BrowseIriView.as_view(), name='browse-iri'),
    path('ingest', view=RdfIngestView.as_view(), name='ingest-rdf'),
    path('docs/openapi.json', view=OpenapiJsonView.as_view(), name='docs.openapi-json'),
    path('docs/openapi.html', view=OpenapiHtmlView.as_view(), name='docs.openapi-html'),
    re_path(r'docs/?', view=RedirectView.as_view(pattern_name='trove:docs.openapi-html'), name='docs'),
]
