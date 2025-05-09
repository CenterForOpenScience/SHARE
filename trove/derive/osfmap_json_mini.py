from trove.derive.osfmap_json import OsfmapJsonDeriver
from primitive_metadata import primitive_rdf as rdf

PREDICATE_LIST = [
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type',
    'http://purl.org/dc/terms/title',
    'http://purl.org/dc/terms/creator',
    'http://purl.org/dc/terms/created',
    'http://xmlns.com/foaf/0.1/name',
    'http://www.w3.org/2002/07/owl#sameAs',
    'http://purl.org/dc/terms/conformsTo',
    'http://purl.org/dc/terms/dateCopyrighted',
    'http://purl.org/dc/terms/description',
    'http://purl.org/dc/terms/hasPart',
    'http://purl.org/dc/terms/isVersionOf',
    'http://purl.org/dc/terms/modified',
    'http://purl.org/dc/terms/publisher',
    'http://purl.org/dc/terms/rights',
    'http://purl.org/dc/terms/subject',
    'http://purl.org/dc/terms/isPartOf',
    'http://purl.org/dc/terms/identifier',
    'http://www.w3.org/2004/02/skos/core#inScheme',
    'http://www.w3.org/2004/02/skos/core#prefLabel',
    'https://osf.io/vocab/2022/affiliation',
    'https://osf.io/vocab/2022/archivedAt',
    'https://osf.io/vocab/2022/contains',
    'https://osf.io/vocab/2022/hostingInstitution',
    'https://osf.io/vocab/2022/keyword',
    'http://www.w3.org/ns/prov#qualifiedAttribution',
    'https://osf.io/vocab/2022/fileName',
    'https://osf.io/vocab/2022/filePath',
    'https://osf.io/vocab/2022/isContainedBy',
    'https://osf.io/vocab/2022/keyword'
]


class IndexcardJsonDeriver(OsfmapJsonDeriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.convert_tripledict()

    def convert_tripledict(self):
        self.data.tripledict = rdf.tripledict_from_tripleset(
            (_subj, _pred, _obj)
            for (_subj, _pred, _obj) in rdf.iter_tripleset(self.data.tripledict)
            if self._should_keep_predicate(_pred)
        )

    @staticmethod
    def _should_keep_predicate(predicate: str) -> bool:
        return True if predicate in PREDICATE_LIST else True
