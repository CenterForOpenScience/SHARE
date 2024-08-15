from collections import defaultdict
import typing

from primitive_metadata import primitive_rdf as rdf

from share.util.checksum_iri import ChecksumIri

from . import trovesearch_flattery as flattery
from .trovesearch_flattery import TrovesearchFlatteryIndexStrategy as FlatteryStrategy


class TrovesearchNesterlyIndexStrategy(FlatteryStrategy):
    '''a more complicated version of the "flattery" trovesearch strategy

    for `index-value-search` queries that the flatter index can't handle
    '''
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TrovesearchNesterlyIndexStrategy',
        hexdigest='...',
    )

    # override TrovesearchFlatteryIndexStrategy
    def index_mappings(self):
        _mappings = super().index_mappings()
        _namelike_text_mapping = {
            **flattery.TEXT_MAPPING,
            'fields': {'keyword': flattery.KEYWORD_MAPPING},
            'copy_to': 'iri_usage.namelike_text',
        }
        # add nested properties
        # (warning: SLOW, use only when needed (and do be sure to question that need))
        _mappings['properties']['iri_usage'] = {
            'type': 'nested',
            'properties': {
                'iri': flattery.IRI_KEYWORD_MAPPING,  # include sameAs
                'propertypath_from_focus': flattery.KEYWORD_MAPPING,
                'depth_from_focus': flattery.KEYWORD_MAPPING,
                # flattened properties (dynamic sub-properties with keyword values)
                'relative_iri_by_propertypath': flattery.FLATTENED_MAPPING,
                'relative_iri_by_depth': flattery.FLATTENED_MAPPING,
                # text properties (only a few)
                'name_text': _namelike_text_mapping,
                'title_text': _namelike_text_mapping,
                'label_text': _namelike_text_mapping,
                'namelike_text': {'type': 'text'},
            },
        }
        return _mappings

    # override TrovesearchFlatteryIndexStrategy
    class _SourcedocBuilder(FlatteryStrategy._SourcedocBuilder):
        # override TrovesearchFlatteryIndexStrategy._SourcedocBuilder
        def build(self):
            _sourcedoc = super().build()
            _sourcedoc['iri_usage'] = self._nested_iri_usages()
            return _sourcedoc

        def _nested_iri_usages(self) -> list:
            _paths_by_iri: dict[str, set[flattery.Propertypath]] = defaultdict(set)
            for _path, _iris in self._fullwalk.iri_values.items():
                for _iri in _iris:
                    _paths_by_iri[_iri].add(_path)
            return list(filter(bool, (
                self._iri_usage_sourcedoc(_iri, _paths)
                for _iri, _paths in _paths_by_iri.items()
            )))

        def _iri_usage_sourcedoc(self, iri: str, paths: set[flattery.Propertypath]) -> dict | None:
            _shortwalk = self._fullwalk.shortwalk(iri)
            return {
                'iri': self._exact_and_suffuniq_iris(iri, _shortwalk),
                'propertypath_from_focus': list(map(flattery.propertypath_as_keyword, paths)),
                'depth_from_focus': list(map(len, paths)),
                'iri_by_propertypath': self._iris_by_propertypath(_shortwalk),
                'iri_by_depth': self._iris_by_depth(_shortwalk),
                'dynamics': {
                    'text_by_propertypath': self._texts_by_propertypath(_shortwalk),
                    'text_by_depth': self._texts_by_depth(_shortwalk),
                    'date_by_propertypath': self._dates_by_propertypath(_shortwalk),
                },
            }

        def _gather_text_values(self, focus_iri, pathset) -> typing.Iterator[str]:
            for _obj in self.rdfdoc.q(focus_iri, pathset):
                if isinstance(_obj, rdf.Literal):
                    yield _obj.unicode_value

    # override TrovesearchFlatteryIndexStrategy
    class _ValuesearchQueryBuilder(FlatteryStrategy._ValuesearchQueryBuilder):
        ...
