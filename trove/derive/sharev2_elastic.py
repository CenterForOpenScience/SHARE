import datetime
import json
import re

from primitive_metadata import primitive_rdf

from share.util import IDObfuscator
from share import models as share_db
from trove.vocab.namespaces import (
    DCAT,
    DCTERMS,
    FOAF,
    OSFMAP,
    RDF,
    SHAREv2,
    SKOS,
)

from ._base import IndexcardDeriver

# sharev2 types, grouped from most- to least-specific
# (for back-compat, forced to choose only one type)
_SHAREv2_TYPES_BY_SPECIFICITY = (
    {  # most specific
        # AgentWorkRelation subtypes
        SHAREv2.PrincipalInvestigator,
        SHAREv2.PrincipalInvestigatorContact,
    },
    {
        # CreativeWork subtypes
        SHAREv2.Article,
        SHAREv2.Book,
        SHAREv2.ConferencePaper,
        SHAREv2.Dissertation,
        SHAREv2.Preprint,
        SHAREv2.Project,
        SHAREv2.Registration,
        SHAREv2.Report,
        SHAREv2.Thesis,
        SHAREv2.WorkingPaper,
        # Agent subtypes
        SHAREv2.Consortium,
        SHAREv2.Department,
        SHAREv2.Institution,
        # AgentWorkRelation subtypes
        SHAREv2.Creator,
    },
    {
        # CreativeWork subtypes
        SHAREv2.DataSet,
        SHAREv2.Patent,
        SHAREv2.Poster,
        SHAREv2.Publication,
        SHAREv2.Presentation,
        SHAREv2.Repository,
        SHAREv2.Retraction,
        SHAREv2.Software,
        # Agent subtypes
        SHAREv2.Organization,
        SHAREv2.Person,
        # AgentWorkRelation subtypes
        SHAREv2.Contributor,
        SHAREv2.Funder,
        SHAREv2.Host,
        SHAREv2.Publisher,
        # AgentRelation subtypes
        SHAREv2.IsAffiliatedWith,
        SHAREv2.IsEmployedBy,
        SHAREv2.IsMemberOf,
        # WorkRelation subtypes
        SHAREv2.Cites,
        SHAREv2.Compiles,
        SHAREv2.Corrects,
        SHAREv2.Discusses,
        SHAREv2.Disputes,
        SHAREv2.Documents,
        SHAREv2.Extends,
        SHAREv2.IsDerivedFrom,
        SHAREv2.IsPartOf,
        SHAREv2.IsSupplementTo,
        SHAREv2.References,
        SHAREv2.RepliesTo,
        SHAREv2.Retracts,
        SHAREv2.Reviews,
        SHAREv2.UsesDataFrom,
    },
    {  # least specific
        SHAREv2.CreativeWork,
        SHAREv2.Agent,
        SHAREv2.AgentWorkRelation,
        SHAREv2.AgentRelation,
        SHAREv2.WorkRelation,
    },
)


# values that, for the purpose of indexing in elasticsearch, are equivalent to absence
EMPTY_VALUES = (None, '', [])  # type: ignore[var-annotated]


def strip_empty_values(thing):
    if isinstance(thing, dict):
        return {
            k: strip_empty_values(v)
            for k, v in thing.items()
            if v not in EMPTY_VALUES
        }
    if isinstance(thing, list):
        return [
            strip_empty_values(v)
            for v in thing
            if v not in EMPTY_VALUES
        ]
    if isinstance(thing, tuple):
        return tuple(
            strip_empty_values(v)
            for v in thing
            if v not in EMPTY_VALUES
        )
    return thing


class ShareV2ElasticDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        return SHAREv2.sharev2_elastic

    # abstract method from IndexcardDeriver
    @staticmethod
    def derived_datatype_iris() -> tuple[str]:
        return (RDF.JSON,)

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        _allowed_focustype_iris = {
            SHAREv2.CreativeWork,
            OSFMAP.Project,
            OSFMAP.ProjectComponent,
            OSFMAP.Registration,
            OSFMAP.RegistrationComponent,
            OSFMAP.Preprint,
        }
        _focustype_iris = self.data.q(self.focus_iri, RDF.type)
        return _allowed_focustype_iris.isdisjoint(_focustype_iris)

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self):
        _suid = self.upstream_description.indexcard.source_record_suid
        try:  # maintain doc id in the sharev2 index
            _suid = _suid.get_backcompat_sharev2_suid()
        except share_db.SourceUniqueIdentifier.DoesNotExist:
            pass  # ok, use the actual suid
        _source_name = _suid.source_config.source.long_title
        _subjects, _subject_synonyms = self._subjects_and_synonyms(_source_name)
        _derived_sharev2 = {
            ###
            # metadata about the record/indexcard in this system
            'id': IDObfuscator.encode(_suid),
            'indexcard_id': self.upstream_description.indexcard.id,
            'date_created': self.upstream_description.indexcard.created.isoformat(),
            'date_modified': self.upstream_description.modified.isoformat(),
            'sources': [_source_name],
            'source_config': _suid.source_config.label,
            'source_unique_id': _suid.identifier,
            ###
            # metadata about the resource in some other system
            'type': self._single_type(self.focus_iri),
            'types': self._type_list(self.focus_iri),
            'date': self._single_date(DCTERMS.date, DCTERMS.created, DCTERMS.modified),
            'date_published': self._single_date(DCTERMS.created, DCTERMS.date),
            'date_updated': self._single_date(DCTERMS.modified, DCTERMS.date),
            'description': self._single_string(DCTERMS.description),
            'justification': self._single_string(OSFMAP.withdrawalJustification),
            'language': self._single_string(DCTERMS.language),
            'registration_type': self._single_string(OSFMAP.registration_type),
            'retracted': bool(self._single_value(OSFMAP.dateWithdrawn)),
            'title': self._single_string(DCTERMS.title),
            'withdrawn': bool(self._single_value(OSFMAP.dateWithdrawn)),
            'identifiers': self._string_list(DCTERMS.identifier),
            'tags': self._string_list(OSFMAP.keyword),
            'subjects': _subjects,
            'subject_synonyms': _subject_synonyms,
            # related names:
            'affiliations': self._related_names(OSFMAP.affiliatedInstitution),
            'contributors': self._related_names(DCTERMS.contributor, DCTERMS.creator),
            'funders': self._related_names(OSFMAP.funder),
            'publishers': self._related_names(DCTERMS.publisher),
            'hosts': self._related_names(DCAT.accessService),
            # osf-specific extra
            'osf_related_resource_types': self._osf_related_resource_types(),
            # a bunch of nested data because reasons -- used mostly for rendering search results
            'lists': {
                'affiliations': self._related_agent_list(OSFMAP.affiliatedInstitution),
                'contributors': self._related_agent_list(DCTERMS.contributor, DCTERMS.creator),
                'funders': self._related_agent_list(OSFMAP.funder),
                'publishers': self._related_agent_list(DCTERMS.publisher),
                'hosts': self._related_agent_list(DCAT.accessService),
                'lineage': self._work_lineage_list(self.focus_iri),
            },
        }
        return json.dumps(
            strip_empty_values(_derived_sharev2),
            sort_keys=True,
        )

    def _related_names(self, *predicate_iris):
        _obj_iter = self.data.q(
            self.focus_iri,
            {
                _predicate_iri: FOAF.name
                for _predicate_iri in predicate_iris
            },
        )
        return [
            _obj_to_string_or_none(_obj)
            for _obj in _obj_iter
        ]

    def _single_date(self, *predicate_iris, focus_iri=None):
        _val = self._single_value(*predicate_iris, focus_iri=focus_iri)
        if isinstance(_val, primitive_rdf.Literal):
            return _val.unicode_value
        if isinstance(_val, datetime.date):
            return _val.isoformat()
        return _val

    def _single_string(self, *predicate_iris, focus_iri=None):
        return _obj_to_string_or_none(self._single_value(*predicate_iris, focus_iri=focus_iri))

    def _single_value(self, *predicate_iris, focus_iri=None):
        # for sharev2 back-compat, some fields must have a single value
        # (tho now the corresponding rdf property may have many values)
        for _pred in predicate_iris:
            _object_iter = self.data.q(
                focus_iri or self.focus_iri,
                _pred,  # one at a time to preserve given order
            )
            try:
                return next(_object_iter)
            except StopIteration:
                continue
        return None

    def _string_list(self, *predicate_paths, focus_iri=None):
        _object_iter = self.data.q(
            focus_iri or self.focus_iri,
            predicate_paths,
        )
        return sorted(
            _obj_to_string_or_none(_obj)
            for _obj in _object_iter
        )

    def _osf_related_resource_types(self) -> dict[str, bool]:
        _osf_artifact_types = {
            'analytic_code': OSFMAP.hasAnalyticCodeResource,
            'data': OSFMAP.hasDataResource,
            'materials': OSFMAP.hasMaterialsResource,
            'papers': OSFMAP.hasPapersResource,
            'supplements': OSFMAP.hasSupplementalResource,
        }
        _focus_predicates = set(self.data.tripledict[self.focus_iri].keys())
        return {
            _key: (_pred in _focus_predicates)
            for _key, _pred in _osf_artifact_types.items()
        }

    def _related_agent_list(self, *predicate_iris, focus_iri=None):
        _agent_list = []
        for _predicate_iri in predicate_iris:
            _agent_iri_iter = self.data.q(
                focus_iri or self.focus_iri,
                _predicate_iri,
            )
            for _agent_iri in _agent_iri_iter:
                _agent_list.append(self._related_agent(_predicate_iri, _agent_iri))
        return _agent_list

    def _related_agent(self, relation_iri, agent_iri):
        return {
            'type': self._single_type(agent_iri),
            'types': self._type_list(agent_iri),
            'name': self._single_string(FOAF.name, focus_iri=agent_iri),
            'identifiers': self._string_list(DCTERMS.identifier, focus_iri=agent_iri),
            'relation': self._format_type_iri(relation_iri),
            'cited_as': self._single_string(FOAF.name, focus_iri=agent_iri),
            # TODO 'order_cited':
        }

    def _single_type_iri(self, type_iris) -> str | None:
        # try SHAREv2 types
        _sharev2_type_iris = set(filter(SHAREv2.__contains__, type_iris))
        if _sharev2_type_iris:
            for _sharev2_typeset in _SHAREv2_TYPES_BY_SPECIFICITY:
                _matching_type_iris = _sharev2_type_iris.intersection(_sharev2_typeset)
                if _matching_type_iris:
                    return _matching_type_iris.pop()  # take any one
        # try for an OSFMAP type
        _osfmap_type_iri = next(filter(OSFMAP.__contains__, type_iris), None)
        if _osfmap_type_iri:
            _typename = primitive_rdf.iri_minus_namespace(_osfmap_type_iri, namespace=OSFMAP)
            # sharev2 backcompat: components are not a separate type
            if _typename == 'RegistrationComponent':
                _typename = 'Registration'
            elif _typename == 'ProjectComponent':
                _typename = 'Project'
            # try for a matching type in SHAREv2, but fall back to CreativeWork
            return self._single_type_iri([SHAREv2[_typename], SHAREv2.CreativeWork])
        return None

    def _single_type(self, focus_iri):
        _type_iris = set(self.data.q(focus_iri, RDF.type))
        _type_iri = self._single_type_iri(_type_iris)
        return (
            self._format_type_iri(_type_iri)
            if _type_iri
            else None
        )

    def _type_list(self, focus_iri):
        return sorted(
            self._format_type_iri(_type_iri)
            for _type_iri in self.data.q(focus_iri, RDF.type)
            if _type_iri in SHAREv2 or _type_iri in OSFMAP
        )

    def _format_type_iri(self, iri):
        if iri in SHAREv2:
            _typename = primitive_rdf.iri_minus_namespace(iri, namespace=SHAREv2)
        elif iri in OSFMAP:
            _typename = primitive_rdf.iri_minus_namespace(iri, namespace=OSFMAP)
        else:
            return iri  # oh well
        return self._format_typename(_typename)

    def _format_typename(self, sharev2_typename: str):
        # convert from PascalCase to lower case with spaces between words
        return re.sub(r'\B([A-Z])', r' \1', sharev2_typename).lower()

    def _work_lineage_list(self, work_iri):
        # expects a linear lineage (each resource only "part of" one other)
        _parent_iri = self._single_value(DCTERMS.isPartOf, focus_iri=work_iri)
        if isinstance(_parent_iri, str):
            _parent_lineage_list = self._work_lineage_list(_parent_iri)
            return [
                *_parent_lineage_list,
                self._work_lineage_item(_parent_iri),
            ]
        else:
            return []

    def _work_lineage_item(self, work_iri):
        return {
            'type': self._single_type(work_iri),
            'types': self._type_list(work_iri),
            'title': self._single_string(DCTERMS.title, focus_iri=work_iri),
            'identifiers': self._string_list(DCTERMS.identifier, focus_iri=work_iri),
        }

    def _subjects_and_synonyms(self, source_name):
        _subjects = []
        _subject_synonyms = []
        # making extra osf-specific assumptions here
        for _subject in self.data.q(self.focus_iri, DCTERMS.subject):
            if isinstance(_subject, str):
                _bepress_lineage = self._subject_lineage(_subject, SKOS.prefLabel)
                _source_specific_lineage = self._subject_lineage(_subject, SKOS.altLabel)
                if _source_specific_lineage:
                    _subjects.append(_serialize_subject(source_name, _source_specific_lineage))
                    if _bepress_lineage:
                        _subject_synonyms.append(_serialize_subject('bepress', _bepress_lineage))
                elif _bepress_lineage:
                    _subjects.append(_serialize_subject('bepress', _bepress_lineage))
        return _subjects, _subject_synonyms

    def _subject_lineage(self, subject_iri, label_predicate_iri, visiting_set=None) -> tuple[str, ...]:
        _visiting_set = visiting_set or set()
        _visiting_set.add(subject_iri)
        _labeltext = next(self.data.q(subject_iri, label_predicate_iri), None)
        if not isinstance(_labeltext, primitive_rdf.Literal):
            return ()
        _parent = next(self.data.q(subject_iri, SKOS.broader), None)
        if _parent and (_parent not in _visiting_set):
            _parent_lineage = self._subject_lineage(_parent, label_predicate_iri, _visiting_set)
            return (*_parent_lineage, _labeltext.unicode_value)
        return (_labeltext.unicode_value,)


def _serialize_subject(taxonomy_name: str, subject_lineage: tuple[str, ...]) -> str:
    return '|'.join((taxonomy_name, *subject_lineage))


def _obj_to_string_or_none(obj):
    if obj is None:
        return None
    if isinstance(obj, primitive_rdf.Literal):
        return obj.unicode_value
    return str(obj)
