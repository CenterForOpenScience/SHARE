import gather


TROVE = gather.IriNamespace('https://trove.example/')


CARDSEARCH = gather.GatheringNorms(
    focustype_iris={
        TROVE.Card,
        TROVE.Cardsearch,
        TROVE.Propertysearch,
        TROVE.Valuesearch,
    },
    namestory=(
        gather.Text('cardsearch', language_iris={
            TROVE.word,
            gather.IANA_LANGUAGE['en'],
        }),
        gather.Text('search for index cards that describe items', language_iris={
            TROVE.phrase,
            gather.IANA_LANGUAGE['en'],
        }),
    ),
    attribute_vocab_by_focustype={
        'cardCount': TROVE.cardCount,
        'cardSearchText': TROVE.cardSearchText,
        'propertySearchText': TROVE.propertySearchText,
        'valueSearchText': TROVE.valueSearchText,
        'cardSearchFilter': TROVE.cardSearchFilter,
        'propertySearchFilter': TROVE.propertySearchFilter,
        'valueSearchFilter': TROVE.valueSearchFilter,
        'matchEvidence': TROVE.matchEvidence,
        'resourceIdentifier': TROVE.resourceIdentifier,
        'resourceMetadata': TROVE.resourceMetadata,
        'matchingHighlight': TROVE.matchingHighlight,
    },
    relationship_vocab={
        'evidenceCard': TROVE.evidenceCard,
        'relatedPropertysearch': TROVE.relatedPropertysearch,
        'indexCard': TROVE.indexCard,
        'searchResult': TROVE.searchResult,
    },
)
