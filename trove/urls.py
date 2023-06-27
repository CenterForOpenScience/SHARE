from django.urls import path

from .views.browse import BrowseIriView
from .views.ingest import RdfIngestView
from share.search.views import (
    CardsearchView,
    PropertysearchView,
    ValuesearchView,
)


app_name = 'trove'

urlpatterns = [
    path('index-card-search', view=CardsearchView.as_view(), name='index-card-search'),
    path('index-property-search', view=PropertysearchView.as_view(), name='index-property-search'),
    path('index-value-search', view=ValuesearchView.as_view(), name='index-value-search'),
    path('browse///<path:iri>', view=BrowseIriView.as_view(), name='browse-iri'),
    path('ingest', view=RdfIngestView.as_view(), name='ingest-rdf'),
]
