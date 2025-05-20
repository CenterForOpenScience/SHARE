from trove.vocab import namespaces as ns
from trove.derive.osfmap_json import OsfmapJsonDeriver
from trove.vocab.namespaces import TROVE

INCLUDED_PREDICATE_SET = frozenset({
    ns.RDF.type,
    ns.DCTERMS.title,
    ns.DCTERMS.creator,
    ns.DCTERMS.date, # new
    ns.DCTERMS.created,
    ns.FOAF.name,
    ns.OWL.sameAs,
    ns.DCTERMS.conformsTo,
    ns.DCTERMS.dateCopyrighted,
    ns.DCTERMS.description,
    ns.DCTERMS.hasPart,
    ns.DCTERMS.isVersionOf,
    ns.DCTERMS.modified,
    ns.DCTERMS.publisher,
    ns.DCTERMS.rights,
    ns.DCTERMS.subject,
    ns.DCTERMS.isPartOf,
    ns.DCTERMS.identifier,
    ns.SKOS.inScheme,
    ns.SKOS.prefLabel,
    ns.OSFMAP.affiliation,
    ns.OSFMAP.archivedAt,
    ns.DCTERMS.dateAccepted,
    ns.DCTERMS.dateModified,
    ns.OSFMAP.hostingInstitution,
    ns.OSFMAP.keyword,
    ns.OSFMAP.contains,
    ns.OSFMAP.fileName,
    ns.OSFMAP.filePath,
    ns.OSFMAP.isContainedBy
})

class IndexcardJsonDeriver(OsfmapJsonDeriver):
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
        return True if predicate in INCLUDED_PREDICATE_SET else False
