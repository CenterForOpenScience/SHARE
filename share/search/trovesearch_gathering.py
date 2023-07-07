import json
import typing

from django.conf import settings
import gather

from share import models as share_db
from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
)
from share.search.rdf_as_jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
    JSONAPI_ATTRIBUTE,
)
from share.util import IDObfuscator
from share.util.rdfutil import IriLabeler
from trove import models as trove_db


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
        JSONAPI_MEMBERNAME: {
            gather.text('index-card', language_tag='en'),
        },
    },
    TROVE.Cardsearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-card-search', language_tag='en'),
        },
    },
    TROVE.Propertysearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-property-search', language_tag='en'),
        },
    },
    TROVE.Valuesearch: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('index-value-search', language_tag='en'),
        },
    },
    TROVE.SearchResult: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('search-result', language_tag='en'),
        },
    },
    TROVE.TextMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('TextMatchEvidence', language_tag='en'),
        },
    },
    TROVE.IriMatchEvidence: {
        gather.RDF.type: {gather.RDFS.Class},
        JSONAPI_MEMBERNAME: {
            gather.text('IriMatchEvidence', language_tag='en'),
        },
    },

    # attributes:
    TROVE.totalResultCount: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('totalResultCount', language_tag='en'),
        },
    },
    TROVE.cardsearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchText', language_tag='en'),
        },
    },
    TROVE.propertysearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchText', language_tag='en'),
        },
    },
    TROVE.valuesearchText: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchText', language_tag='en'),
        },
    },
    TROVE.cardsearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('cardSearchFilter', language_tag='en'),
        },
    },
    TROVE.propertysearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('propertySearchFilter', language_tag='en'),
        },
    },
    TROVE.valuesearchFilter: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('valueSearchFilter', language_tag='en'),
        },
    },
    TROVE.matchEvidence: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchEvidence', language_tag='en'),
        },
    },
    TROVE.resourceIdentifier: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceIdentifier', language_tag='en'),
        },
    },
    TROVE.resourceMetadata: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('resourceMetadata', language_tag='en'),
        },
    },
    TROVE.matchingHighlight: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_ATTRIBUTE},
        JSONAPI_MEMBERNAME: {
            gather.text('matchingHighlight', language_tag='en'),
        },
    },
    TROVE.propertyPath: {
        gather.RDF.type: {gather.OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('propertyPath', language_tag='en'),
        },
    },
    TROVE.filterType: {
        gather.RDF.type: {gather.OWL.FunctionalProperty},
        JSONAPI_MEMBERNAME: {
            gather.text('filterType', language_tag='en'),
        },
    },
    TROVE.filterValue: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('filterValue', language_tag='en'),
        },
    },

    # relationships:
    TROVE.searchResult: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('searchResultPage', language_tag='en'),
        },
    },
    TROVE.evidenceCard: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('evidenceCard', language_tag='en'),
        },
    },
    TROVE.relatedPropertysearch: {
        gather.RDF.type: {gather.RDF.Property, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('relatedPropertySearch', language_tag='en'),
        },
    },
    TROVE.indexCard: {
        gather.RDF.type: {gather.OWL.FunctionalProperty, JSONAPI_RELATIONSHIP},
        JSONAPI_MEMBERNAME: {
            gather.text('indexCard', language_tag='en'),
        },
    },

    # values:
    TROVE['ten-thousands-and-more']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('ten-thousands-and-more', language_tag='en'),
        },
    },
    TROVE['any-of']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('any-of', language_tag='en'),
        },
    },
    TROVE['none-of']: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('none-of', language_tag='en'),
        },
    },
    TROVE.before: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('before', language_tag='en'),
        },
    },
    TROVE.after: {
        gather.RDF.type: {gather.RDF.Property},
        JSONAPI_MEMBERNAME: {
            gather.text('after', language_tag='en'),
        },
    },
}


TROVESEARCH = gather.GatheringNorms(
    namestory=(
        gather.text('cardsearch', language_tag='en'),
        gather.text('search for index cards that describe resources', language_tag='en'),
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
        gather.text('trove search', language_tag='en'),
    ),
    norms=TROVESEARCH,
    gatherer_kwargnames={'search_params', 'specific_index'},
)

trovesearch_labeler = IriLabeler(TROVESEARCH_VOCAB, label_iri=JSONAPI_MEMBERNAME)


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchText)
def gather_cardsearch_text(focus, *, specific_index, search_params):
    yield (TROVE.cardsearchText, gather.text(search_params.cardsearch_text, language_iris=()))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchText)
def gather_propertysearch_text(focus, *, specific_index, search_params):
    yield (TROVE.propertysearchText, gather.text(search_params.propertysearch_text, language_iris=()))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchText)
def gather_valuesearch_text(focus, *, specific_index, search_params):
    yield (TROVE.valuesearchText, gather.text(search_params.valuesearch_text, language_iris=()))


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchFilter)
def gather_cardsearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.cardsearch_filter_set:
        yield (TROVE.cardsearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchFilter)
def gather_propertysearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.propertysearch_filter_set:
        yield (TROVE.propertysearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchFilter)
def gather_valuesearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.valuesearch_filter_set:
        yield (TROVE.valuesearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.totalResultCount,
    TROVE.searchResult,
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, CardsearchParams)
    _cardsearch_resp = specific_index.pls_handle_cardsearch(search_params)
    yield (TROVE.totalResultCount, _cardsearch_resp.total_result_count)
    for _result in _cardsearch_resp.search_result_page:
        yield (_result.card_iri, gather.RDF.type, TROVE.Card)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (gather.RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                # TODO: card_iri (for propertysearch, valuesearch)
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (gather.RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Propertysearch},
)
def gather_propertysearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, PropertysearchParams)
    _propertysearch_resp = specific_index.pls_handle_propertysearch(search_params)
    yield (TROVE.totalResultCount, _propertysearch_resp.total_result_count)
    for _result in _propertysearch_resp.search_result_page:
        yield (_result.card_iri, gather.RDF.type, TROVE.Card)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (gather.RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.card, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (gather.RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, ValuesearchParams)
    _valuesearch_resp = specific_index.pls_handle_valuesearch(search_params)
    yield (TROVE.WOOP, gather.text(json.dumps(_valuesearch_resp), language_iris={gather.RDF.JSON}))
    return  # TODO
    yield (TROVE.totalResultCount, _valuesearch_resp.total_result_count)
    for _result in _valuesearch_resp.search_result_page:
        yield (_result.card_iri, gather.RDF.type, TROVE.Card)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (gather.RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.card, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (gather.RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Card},
)
def gather_card(focus, *, specific_index, search_params):
    _focus_iris_qs = trove_db.ResourceIdentifier.objects.queryset_for_iris(focus.iris)
    _osfmap_indexcard = (
        trove_db.DerivedIndexcard
        .filter(upriver_card__focus_identifier_set=_focus_iris_qs)
    )
    # TODO: batch gatherer -- load all records in one query
    _suid_id = suid_id_for_card_focus(focus)
    # TODO: load DerivedIndexcard
    _normalized_datum = (
        db.NormalizedData.objects
        .filter(raw__suid_id=_suid_id)
        .order_by('-created_at')
        .first()
    )
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


###
# local helpers

def _filter_as_blanknode(search_filter) -> frozenset:
    _filter_values = (
        (TROVE.filterValue, _value)
        for _value in search_filter.value_set
    )
    return frozenset((
        # property_path is a tuple, which becomes an rdf sequence
        (TROVE.propertyPath, search_filter.property_path),
        (TROVE.filterType, TROVE[search_filter.operator.value]),
        *_filter_values,
    ))
