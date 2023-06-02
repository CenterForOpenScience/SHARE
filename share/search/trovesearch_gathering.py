import json
import typing

from django.conf import settings
import gather

from share import models as db
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
# TODO acrostic
# turtles
# ramble;
# owl
# very
# eyeful.

# some assumed-safe assumptions for iris in trovespace:
# - a name ending in forward slash (`/`) is a namespace
# - an iri fragment (after `#`) is a `,`-separated list
#   of iris; a path of predicates from the root of that
#   index card (for the iri with `#` and after removed)
# - TODO: each iri is an irL that resolves to rdf, html


TROVESEARCH = gather.GatheringNorms(
    namestory=(
        gather.Text('cardsearch', language_iris={
            JSONAPI_MEMBERNAME,
            gather.IANA_LANGUAGE.en,
        }),
        gather.Text('search for index cards that describe items', language_iris={
            TROVE.phrase,
            gather.IANA_LANGUAGE.en,
        }),
    ),
    focustype_iris={
        TROVE.Card,
        TROVE.Cardsearch,
        TROVE.Propertysearch,
        TROVE.Valuesearch,
    },
    gatherer_kwargnames={'search_params'},
    vocabulary={
        # types:
        TROVE.Card: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-card', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.Cardsearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-card-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.Propertysearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-property-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.Valuesearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-value-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.SearchResult: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('search-result', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.TextMatchEvidence: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('TextMatchEvidence', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.IriMatchEvidence: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('IriMatchEvidence', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        # attributes:
        TROVE.totalResultCount: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('totalResultCount', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.cardsearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('cardSearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.propertysearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('propertySearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.valuesearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('valueSearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.cardsearchFilter: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('cardSearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.propertysearchFilter: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('propertySearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.valuesearchFilter: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('valueSearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.matchEvidence: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('matchEvidence', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.resourceIdentifier: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('resourceIdentifier', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.resourceType: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('resourceType', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.resourceMetadata: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('resourceMetadata', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.matchingHighlight: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
            gather.RDFS.label: {
                gather.Text.new('matchingHighlight', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.propertyPath: {
            gather.RDF.type: {gather.OWL.FunctionalProperty},
            gather.RDFS.label: {
                gather.Text.new('propertyPath', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.filterType: {
            gather.RDF.type: {gather.OWL.FunctionalProperty},
            gather.RDFS.label: {
                gather.Text.new('filterType', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.filterValue: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('filterValue', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        # relationships:
        TROVE.searchResult: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
            gather.RDFS.label: {
                gather.Text.new('searchResultPage', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.evidenceCard: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
            gather.RDFS.label: {
                gather.Text.new('evidenceCard', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.relatedPropertysearch: {
            gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
            gather.RDFS.label: {
                gather.Text.new('relatedPropertySearch', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.indexCard: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
            gather.RDFS.label: {
                gather.Text.new('indexCard', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        # filter operator values:
        TROVE['any-of']: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('any-of', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE['none-of']: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('none-of', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.before: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('before', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        TROVE.after: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('after', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
        # other properties:
        gather.RDF.type: {
            gather.RDF.type: {gather.RDF.Property},
            gather.RDFS.label: {
                gather.Text.new('@type', language_iris={
                    gather.IANA_LANGUAGE.en,
                    JSONAPI_MEMBERNAME,
                }),
            },
        },
    },
)


trovesearch = gather.GatheringOrganizer(
    namestory=(),
    norms=TROVESEARCH,
)


@trovesearch.gatherer(TROVE.cardsearchText)
def gather_cardsearch_text(focus, *, search_params):
    yield (TROVE.cardsearchText, gather.Text.new(
        search_params.cardsearch_text,
        language_iris=(),
    ))


@trovesearch.gatherer(TROVE.cardsearchFilter)
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


@trovesearch.gatherer(
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


@trovesearch.gatherer(
    focustype_iris={TROVE.Card},
)
def gather_card(focus, *, search_params):
    # TODO: batch gatherer? load all records in one query
    _suid_id = suid_id_for_card_focus(focus)
    _record = db.FormattedMetadataRecord.objects.get(
        suid_id=_suid_id,
        record_format='sharev2_elastic',  # TODO: better
    )
    _json_metadata = json.loads(_record.formatted_metadata)
    for _identifier in _json_metadata.get('identifiers', ()):
        yield (TROVE.resourceIdentifier, _identifier)
    for _type in _json_metadata.get('types', ()):
        yield (TROVE.resourceType, gather.Text.new(_type, language_iris={TROVE.RandomTypes}))  # TODO: defined iris
    yield (
        TROVE.resourceMetadata,  # TODO: to osfmap
        gather.Text.new(_record.formatted_metadata, language_iris={gather.RDF.JSON})
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
