import json
import typing

from django.conf import settings
import gather

from share import models as db
from share.search import exceptions
from share.search.search_params import CardsearchParams
from share.search.index_strategy import IndexStrategy
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
            TROVE.word,
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
    gathering_kwargnames={'search_params'},
    vocabulary={
        # types:
        TROVE.Card: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-card', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.Cardsearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-card-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.Propertysearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-property-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.Valuesearch: {
            gather.RDF.type: {gather.RDFS.Class},
            gather.RDFS.label: {
                gather.Text.new('index-value-search', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        # attributes:
        TROVE.totalResultCount: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('totalResultCount', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.cardsearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('cardSearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.propertysearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('cardSearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.valuesearchText: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('valueSearchText', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.cardsearchFilter: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('cardSearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.propertysearchFilter: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('propertySearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.valuesearchFilter: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('valueSearchFilter', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.matchEvidence: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('matchEvidence', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.resourceIdentifier: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('resourceIdentifier', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.resourceType: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('resourceType', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.resourceMetadata: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('resourceMetadata', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.matchingHighlight: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('matchingHighlight', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.propertyPath: {
            gather.RDF.type: {gather.OWL.FunctionalProperty, TROVE.Attribute},
            gather.RDFS.label: {
                gather.Text.new('propertyPath', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        # relationships:
        TROVE.searchResult: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Relationship},
            gather.RDFS.label: {
                gather.Text.new('searchResultPage', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.evidenceCard: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Relationship},
            gather.RDFS.label: {
                gather.Text.new('evidenceCard', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.relatedPropertysearch: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Relationship},
            gather.RDFS.label: {
                gather.Text.new('relatedPropertySearch', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
        TROVE.indexCard: {
            gather.RDF.type: {gather.RDF.Property, TROVE.Relationship},
            gather.RDFS.label: {
                gather.Text.new('indexCard', language_iris={
                    gather.IANA_LANGUAGE.en,
                    TROVE.word,
                }),
            },
        },
    },
)


@TROVESEARCH.gatherer(
    TROVE.cardsearchParams,
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch_params(focus, *, search_params):
    assert isinstance(search_params, CardsearchParams)
    # TODO


@TROVESEARCH.gatherer(
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


@TROVESEARCH.gatherer(
    focustype_iris={TROVE.Card},
)
def gather_card(focus, *, search_params):
    # TODO: batch gatherer? load all records in one query
    _suid_id = suid_id_for_card_focus(focus)
    _record = db.FormattedMetadataRecord.objects.get(
        suid_id=_suid_id,
        metadata_format='sharev2_elastic',  # TODO: better
    )
    _json_metadata = json.loads(_record.formatted_metadata)
    yield (TROVE.resourceIdentifier, _json_metadata.get('identifiers', ()))
    yield (TROVE.resourceType, _json_metadata.get('types', ()))
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
