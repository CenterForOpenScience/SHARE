import gather

from share.search import exceptions, search_params
from share.search.index_strategy import IndexStrategy


###
# an iri namespace for troves of metadata
TROVE = gather.IriNamespace('https://share.osf.io/trove/')
# TODO domain from settings
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


def _trove_property_textlabel(iri: str) -> gather.Text:
    return gather.Text.new(
        # assumes that the iri is in the TROVE namespace
        # and the iri name-part is a meaningful label...
        gather.IriNamespace.without_namespace(iri, namespace=TROVE),
        language_iris={
            TROVE.camelCase,          # written in camelCase...
            TROVE.word,               # without any blank space...
            gather.IANA_LANGUAGE.en,  # using english words (like this comment)
        },
    )


def _trove_vocabulary(attribute_iris: set[str], relationship_iris: set[str]) -> gather.RdfTripleDictionary:
    assert not attribute_iris.intersection(relationship_iris)
    _vocabulary = {}
    for _attr_iri in attribute_iris:
        _vocabulary[_attr_iri] = {
            gather.RDF.type: {gather.RDF.Property, TROVE.Attribute},
            gather.RDFS.label: {_trove_property_textlabel(_attr_iri)},
        }
    for _relationship_iri in relationship_iris:
        _vocabulary[_relationship_iri] = {
            gather.RDF.type: {gather.RDF.Property, TROVE.Relationship},
            gather.RDFS.label: {_trove_property_textlabel(_relationship_iri)},
        }
    return _vocabulary


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
    vocabulary=_trove_vocabulary(
        attribute_iris={
            TROVE.totalResultCount,
            TROVE.cardsearchText,
            TROVE.propertysearchText,
            TROVE.valuesearchText,
            TROVE.cardsearchFilter,
            TROVE.propertysearchFilter,
            TROVE.valuesearchFilter,
            TROVE.matchEvidence,
            TROVE.resourceIdentifier,
            TROVE.resourceMetadata,
            TROVE.matchingHighlight,
        },
        relationship_iris={
            TROVE.searchResult,
            TROVE.evidenceCard,
            TROVE.relatedPropertysearch,
            TROVE.indexCard,
        },
    ),
)


@TROVESEARCH.gatherer(
    TROVE.cardsearchParams,
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch_params(focus):
    pass


@TROVESEARCH.gatherer(
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch(focus, cardsearch_params):
    # parse querystring from focus.iris
    # (assume just one iri for now)
    _cardsearch_iri = next(iter(focus.iris))
    _cardsearch_params = search_params.CardsearchParams.from_iri(_cardsearch_iri)
    # run search
    try:
        _specific_index = IndexStrategy.get_for_searching(
            _cardsearch_params.index_strategy_name,
            with_default_fallback=True,
        )
    except exceptions.IndexStrategyError as error:
        raise Exception('TODO: 404') from error
    yield from gather.tripledict_as_tripleset(
        _specific_index.pls_handle_cardsearch(_cardsearch_params),
    )
    # yield totalResultCount
    # yield SearchResult for each hit
    # yield indexcard focus (with suid-id in iri)
    # (skip yielding non-included parts)
    pass


@TROVESEARCH.gatherer(focustype_iris={
    TROVE.Card,
})
def gather_card(focus):
    # TODO:
    # get suid from focus.iris
    # load via FormattedMetadataRecord
    pass
