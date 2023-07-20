import json

from trove.render.jsonld import RdfJsonldRenderer
from trove.vocab.osfmap import OSFMAP_VOCAB, osfmap_labeler
from trove.vocab.trove import TROVE
from ._base import IndexcardDeriver


class OsfmapJsonDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        return TROVE['derive/osfmap_json']

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        return False

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self):
        return json.dumps(
            RdfJsonldRenderer(OSFMAP_VOCAB, osfmap_labeler).tripledict_as_nested_jsonld(
                self.data.tripledict,
                self.focus_iri,
            )
        )
