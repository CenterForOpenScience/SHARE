from trove.vocab import TROVE, OSFMAP
from ._base import IndexcardDeriver


class OsfmapJsonDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        return TROVE['derive/osfmap_json']

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        _allowed_focustype_iris = {
            SHAREv2.AbstractCreativeWork,
            OSFMAP.Project,
            OSFMAP.ProjectComponent,
            OSFMAP.Registration,
            OSFMAP.RegistrationComponent,
            OSFMAP.Preprint,
        }
        _focustype_iris = gather.objects_by_pathset(self.tripledict, self.focus_iri, RDF.type)
        return _allowed_focustype_iris.isdisjoint(_focustype_iris)

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self):
        try:  # maintain doc id in the sharev2 index
            _suid = self.upriver_card.get_backcompat_sharev2_suid()
        except share_db.SourceUniqueIdentifier.DoesNotExist:
            _suid = self.upriver_card.get_suid()
