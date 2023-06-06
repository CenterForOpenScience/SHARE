import json
import typing

from django.conf import settings
import gather

from share import models as db
from share.metadata_formats.osfmap_jsonld import OsfmapJsonldFormatter
from share.search import exceptions
from share.search.search_params import CardsearchParams
from share.search.index_strategy import IndexStrategy
from share.search.rdf_as_jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
    JSONAPI_ATTRIBUTE,
)
from share.util import IDObfuscator


###
# an iri namespace for troves of metadata
TROVE = gather.IriNamespace('https://share.osf.io/vocab/trove/')

# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html

TROVESEARCH_VOCAB: gather.RdfTripleDictionary = {

    # types:
    TROVE.Card: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('index-card', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.Cardsearch: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('index-card-search', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.Propertysearch: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('index-property-search', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.Valuesearch: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('index-value-search', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.SearchResult: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('search-result', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.TextMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('TextMatchEvidence', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.IriMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        gather.RDFS.label: {
            gather.text('IriMatchEvidence', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },

    # attributes:
    TROVE.totalResultCount: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('totalResultCount', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.cardsearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('cardSearchText', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.propertysearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('propertySearchText', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.valuesearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('valueSearchText', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.cardsearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('cardSearchFilter', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.propertysearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('propertySearchFilter', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.valuesearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('valueSearchFilter', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.matchEvidence: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('matchEvidence', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.resourceIdentifier: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('resourceIdentifier', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.resourceMetadata: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('resourceMetadata', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.matchingHighlight: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        gather.RDFS.label: {
            gather.text('matchingHighlight', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.propertyPath: {
        gather.RDF.type: {gather.OWL.FunctionalProperty},
        gather.RDFS.label: {
            gather.text('propertyPath', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.filterType: {
        gather.RDF.type: {gather.OWL.FunctionalProperty},
        gather.RDFS.label: {
            gather.text('filterType', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.filterValue: {
        gather.RDF.type: {gather.RDF.Property},
        gather.RDFS.label: {
            gather.text('filterValue', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },

    # relationships:
    TROVE.searchResult: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        gather.RDFS.label: {
            gather.text('searchResultPage', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.evidenceCard: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        gather.RDFS.label: {
            gather.text('evidenceCard', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.relatedPropertysearch: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        gather.RDFS.label: {
            gather.text('relatedPropertySearch', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.indexCard: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        gather.RDFS.label: {
            gather.text('indexCard', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },

    # filter operator values:
    TROVE['any-of']: {
        gather.RDF.type: {gather.RDF.Property},
        gather.RDFS.label: {
            gather.text('any-of', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE['none-of']: {
        gather.RDF.type: {gather.RDF.Property},
        gather.RDFS.label: {
            gather.text('none-of', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.before: {
        gather.RDF.type: {gather.RDF.Property},
        gather.RDFS.label: {
            gather.text('before', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
    TROVE.after: {
        gather.RDF.type: {gather.RDF.Property},
        gather.RDFS.label: {
            gather.text('after', language_iris={
                gather.IANA_LANGUAGE.en,
                JSONAPI_MEMBERNAME,
            }),
        },
    },
}


TROVESEARCH = gather.GatheringNorms(
    namestory=(
        gather.Text('cardsearch', language_iris={
            JSONAPI_MEMBERNAME,
            gather.IANA_LANGUAGE.en,
        }),
        gather.Text('search for index cards that describe resources', language_iris={
            gather.IANA_LANGUAGE.en,
        }),
    ),
    focustype_iris={
        TROVE.Card,
        TROVE.Cardsearch,
        TROVE.Propertysearch,
        TROVE.Valuesearch,
    },
    vocabulary=TROVESEARCH_VOCAB,
)


trovesearch_by_indexstrategy = gather.GatheringOrganizer(
    namestory=(
        gather.text('trove search', language_iris={gather.IANA_LANGUAGE.en}),
    ),
    norms=TROVESEARCH,
    gatherer_kwargnames={'search_params'},
)


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchText)
def gather_cardsearch_text(focus, *, search_params):
    yield (TROVE.cardsearchText, gather.text(
        search_params.cardsearch_text,
        language_iris=(),
    ))


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchFilter)
def gather_cardsearch_filter(focus, *, search_params):
    for _filter in search_params.cardsearch_filter_set:
        _filter_values = (
            (TROVE.filterValue, _value)
            for _value in _filter.value_set
        )
        yield (TROVE.cardsearchFilter, frozenset((
            (TROVE.propertyPath, _filter.property_path),  # tuple => sequence
            (TROVE.filterType, TROVE[_filter.operator.value]),
            *_filter_values,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch(focus, *, search_params):
    assert isinstance(search_params, CardsearchParams)
    try:
        _specific_index = IndexStrategy.get_for_searching(
            search_params.index_strategy_name,
            with_default_fallback=True,
        )
    except exceptions.IndexStrategyError as error:
        raise Exception('TODO: 404') from error
    yield from _specific_index.pls_handle_cardsearch(search_params)


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Card},
)
def gather_card(focus, *, search_params):
    # TODO: batch gatherer -- load all records in one query
    _suid_id = suid_id_for_card_focus(focus)
    _normalized_datum = (
        db.NormalizedData.objects
        .filter(raw__suid_id=_suid_id)
        .order_by('-created_at')
        .first()
    )
    # TODO: when osfmap formatter is solid, store as formatted record instead
    # _record = db.FormattedMetadataRecord.objects.get_or_create_formatted_record(
    #     suid_id=_suid_id,
    #     record_format='osfmap_jsonld',
    # )
    _resource_metadata = OsfmapJsonldFormatter().format(_normalized_datum)
    # TODO: do not parse the json here -- store identifiers by suid
    _json_metadata = json.loads(_resource_metadata)
    for _identifier_obj in _json_metadata.get('identifier', ()):
        yield (
            TROVE.resourceIdentifier,
            gather.text(_identifier_obj['@value'], language_iris=()),
        )
    yield (
        TROVE.resourceMetadata,
        gather.text(_resource_metadata, language_iris={gather.RDF.JSON})
    )


###
# non-trove share iris
SHARE_SUID = gather.IriNamespace(f'{settings.SHARE_API_URL}api/v2/suids/')


def suid_id_for_card_focus(focus) -> str:
    try:
        _suid_iri = next(
            _iri
            for _iri in focus.iris
            if _iri in SHARE_SUID
        )
    except StopIteration:
        raise ValueError(f'expected an iri starting with "{SHARE_SUID}", got {focus.iris}')
    return IDObfuscator.decode_id(
        gather.IriNamespace.without_namespace(_suid_iri, namespace=SHARE_SUID),
    )


def card_iri_for_suid(*, suid_id: typing.Union[str, int]) -> str:
    _suid_id = (
        suid_id
        if isinstance(suid_id, str)
        else IDObfuscator.encode_id(suid_id, db.SourceUniqueIdentifier)
    )
    return SHARE_SUID[_suid_id]
