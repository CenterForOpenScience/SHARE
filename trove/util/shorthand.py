from primitive_metadata import primitive_rdf as rdf


def build_shorthand_from_thesaurus(
    thesaurus: rdf.RdfTripleDictionary,
    label_predicate: str,
    base_shorthand: rdf.IriShorthand | None = None
) -> rdf.IriShorthand:
    _prefixmap = {}
    for _iri, _twoples in thesaurus.items():
        _labelset = _twoples.get(label_predicate)
        if not _labelset:
            continue
        if len(_labelset) > 1:
            raise ValueError(f'ambiguous labels for iri "{_iri}": {_labelset}')
        (_label,) = _labelset
        _prefixmap[_label.unicode_value] = _iri
    return (
        rdf.IriShorthand(_prefixmap)
        if base_shorthand is None
        else base_shorthand.with_update(_prefixmap)
    )
