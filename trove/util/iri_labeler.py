from typing import Optional

from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import RDFS


class IriLabeler:
    def __init__(
        self,
        vocabulary: primitive_rdf.RdfTripleDictionary,
        label_iri: str = RDFS.label,
        acceptable_prefixes: tuple[str] = (),
        output_prefix: Optional[str] = None,
    ):
        self.vocabulary = vocabulary
        self.label_iri = label_iri
        self.acceptable_prefixes = acceptable_prefixes
        self.output_prefix = output_prefix

    def build_shorthand(self) -> primitive_rdf.IriShorthand:
        return primitive_rdf.IriShorthand({
            _label: _iri
            for _label, _iri in self.all_iris_by_label()
        })

    def all_iris_by_label(self) -> dict[str, str]:
        try:
            return self.__iris_by_label
        except AttributeError:
            _iris_by_label = {}
            for _iri in self.vocabulary:
                try:
                    _iris_by_label[self._find_label(_iri)] = _iri
                except ValueError:
                    pass  # no label, is ok
            self.__iris_by_label = _iris_by_label
            return _iris_by_label

    def all_labels_by_iri(self) -> dict[str, str]:
        try:
            return self.__labels_by_iri
        except AttributeError:
            _iris_by_label = self.all_iris_by_label()
            _labels_by_iri = {
                _iri: _label
                for _label, _iri in _iris_by_label.items()
            }
            _missing_iris = (
                set(_iris_by_label.values())
                .difference(_labels_by_iri.keys())
            )
            if _missing_iris:
                raise ValueError(f'vocab label collision! missing labels for {_missing_iris}')
            self.__labels_by_iri = _labels_by_iri
            return _labels_by_iri

    def iri_for_label(self, label: str, *, default=None) -> str:
        _labelkey = label
        for _prefix in self.acceptable_prefixes:
            if label.startswith(_prefix):
                _labelkey = label[len(_prefix):]  # remove prefix
        if default:
            return self.all_iris_by_label().get(_labelkey, default)
        return self.all_iris_by_label()[_labelkey]  # may raise KeyError

    def label_for_iri(self, iri: str) -> str:
        _label = self.all_labels_by_iri()[iri]  # may raise KeyError
        return (
            ''.join((self.output_prefix, _label))
            if self.output_prefix
            else _label
        )

    def get_label_or_iri(self, iri: str) -> str:
        try:
            return self.label_for_iri(iri)
        except KeyError:
            return iri

    def _find_label(self, iri: str) -> str:
        _labelset = (
            self.vocabulary
            .get(iri, {})
            .get(self.label_iri, ())
        )
        try:
            return next(
                _label.unicode_value
                for _label in _labelset
                if isinstance(_label, primitive_rdf.Literal)
            )
        except StopIteration:
            raise ValueError(f'could not find label for iri "{iri}"')
