from django.urls import path

from .views.browse import BrowseIriView
from .views.ingest import RdfIngestView
from .views.indexcard import IndexcardView
from .views.search import (
    CardsearchView,
    ValuesearchView,
)
from .views.docs import OpenapiJsonView


app_name = 'trove'

urlpatterns = [
    path('index-card/<uuid:indexcard_uuid>', view=IndexcardView.as_view(), name='index-card'),
    path('index-card-search', view=CardsearchView.as_view(), name='index-card-search'),
    path('index-value-search', view=ValuesearchView.as_view(), name='index-value-search'),
    path('browse///<path:iri>', view=BrowseIriView.as_view(), name='browse-iri'),
    path('ingest', view=RdfIngestView.as_view(), name='ingest-rdf'),
    path('openapi.json', view=OpenapiJsonView.as_view(), name='openapi'),
]
