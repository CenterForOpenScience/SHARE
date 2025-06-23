from trove.vocab import namespaces as ns
from trove.derive.osfmap_json import OsfmapJsonFullDeriver
from trove.vocab.namespaces import TROVE

EXCLUDED_PREDICATE_SET = frozenset({
    ns.OSFMAP.contains,
})


class OsfmapJsonMiniDeriver(OsfmapJsonFullDeriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.convert_tripledict()

    @staticmethod
    def deriver_iri() -> str:
        return TROVE['derive/osfmap_json']

    def convert_tripledict(self):
        self.data.tripledict = {
            _subj: _new_twopledict
            for _subj, _old_twopledict in self.data.tripledict.items()
            if (_new_twopledict := {
                _pred: _obj_set
                for _pred, _obj_set in _old_twopledict.items()
                if self._should_keep_predicate(_pred)
            })
        }

    @staticmethod
    def _should_keep_predicate(predicate: str) -> bool:
        return predicate not in EXCLUDED_PREDICATE_SET
