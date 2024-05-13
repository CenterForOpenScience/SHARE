from trove.render.jsonld import RdfJsonldRenderer
from trove.vocab.osfmap import OSFMAP_VOCAB, osfmap_shorthand
from trove.vocab.namespaces import TROVE
from ._base import IndexcardDeriver


def get_osfmap_renderer() -> RdfJsonldRenderer:
    return RdfJsonldRenderer(
        thesaurus=OSFMAP_VOCAB,
        iri_shorthand=osfmap_shorthand(),
    )


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
        return get_osfmap_renderer().render_document(
            self.data.tripledict,
            self.focus_iri,
        )
