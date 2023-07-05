from trove.vocab import TROVE


class TrovesearchNestedDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        return TROVE['IndexcardDeriver/nested']

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        return False

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self):
