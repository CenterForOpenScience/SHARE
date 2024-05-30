from primitive_metadata import primitive_rdf as rdf


def build_shorthand_from_thesaurus(
    thesaurus: rdf.RdfTripleDictionary,
    label_predicate: str,
    base_shorthand: rdf.IriShorthand | None = None
) -> rdf.IriShorthand:
    _prefixmap = {}
    for _iri, _twoples in thesaurus.items():
        for _label in _twoples.get(label_predicate, ()):
            _prefixmap[_label.unicode_value] = _iri
    return (
        rdf.IriShorthand(_prefixmap)
        if base_shorthand is None
        else base_shorthand.with_update(_prefixmap)
    )
