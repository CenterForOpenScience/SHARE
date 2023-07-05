import datetime
import json
import re

import gather

from share.schema import ShareV2Schema
from share.util import IDObfuscator
from share import models as share_db
from trove.vocab import DCTERMS, FOAF, RDF, DCAT, SHAREv2
from trove.vocab.osfmap import OSFMAP

from ._base import IndexcardDeriver


# values that, for the purpose of indexing in elasticsearch, are equivalent to absence
EMPTY_VALUES = (None, '')


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
        _source_name = _suid.source_config.source.long_title
        _derived_sharev2 = {
            ###
            # metadata about the record/indexcard in this system
            'id': IDObfuscator.encode(_suid),
            'indexcard_id': self.upriver_card.id,
            'rawdatum_id': self.upriver_card.from_raw_datum_id,
            'date_created': _suid.get_date_first_seen().isoformat(),
            'date_modified': self.upriver_card.modified.isoformat(),
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
            'retracted': bool(self._single_string(OSFMAP.dateWithdrawn)),
            'title': self._single_string(DCTERMS.title),
            'withdrawn': self._single_string(OSFMAP.dateWithdrawn),
            'identifiers': self._string_list(DCTERMS.identifier),
            'tags': self._string_list(OSFMAP.keyword),
            'subjects': self._string_list(DCTERMS.subject),
            'subject_synonyms': self._string_list(DCTERMS.subject),
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
        _obj_iter = gather.objects_by_pathset(
            self.tripledict,
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
        _val = self._single_value(predicate_iris, focus_iri)
        if isinstance(_val, datetime.date):
            return _val.isoformat()
        return _val

    def _single_string(self, *predicate_iris, focus_iri=None):
        return _obj_to_string_or_none(self._single_value(predicate_iris, focus_iri))

    def _single_value(self, *predicate_iris, focus_iri=None):
        # for sharev2 back-compat, some fields must have a single value
        # (tho now the corresponding rdf property may have many values)
        for _pred in predicate_iris:
            _object_iter = gather.objects_by_pathset(
                self.tripledict,
                focus_iri or self.focus_iri,
                _pred,  # one at a time to preserve given order
            )
            try:
                return next(_object_iter)
            except StopIteration:
                continue
        return None

    def _string_list(self, *predicate_iris, focus_iri=None):
        _object_iter = gather.objects_by_pathset(
            self.tripledict,
            focus_iri or self.focus_iri,
            predicate_iris,
        )
        return [
            _obj_to_string_or_none(_obj)
            for _obj in _object_iter
        ]

    def _osf_related_resource_types(self) -> dict[str, bool]:
        _osf_artifact_types = {
            'analytic_code': OSFMAP.hasAnalyticCodeResource,
            'data': OSFMAP.hasDataResource,
            'materials': OSFMAP.hasMaterialsResource,
            'papers': OSFMAP.hasPapersResource,
            'supplements': OSFMAP.hasSupplementalResource,
        }
        _focus_twopledict = self.tripledict[self.focus_iri]
        return {
            _key: (_iri in _focus_twopledict)
            for _key, _iri in _osf_artifact_types.items()
        }

    def _related_agent_list(self, *predicate_iris, focus_iri=None):
        _agent_list = []
        for _predicate_iri in predicate_iris:
            _agent_iri_iter = gather.objects_by_pathset(
                self.tripledict,
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

    def _sharev2_type(self, type_iri):
        try:
            _typename = gather.IriNamespace.without_namespace(type_iri, namespace=SHAREv2)
        except ValueError:
            return None
        else:
            return ShareV2Schema().get_type(_typename)

    def _single_type(self, focus_iri):
        def _type_sortkey(sharev2_type):
            return sharev2_type.distance_from_concrete_type()
        _types = filter(None, (
            self._sharev2_type(_type_iri)
            for _type_iri in gather.objects_by_pathset(
                self.tripledict,
                focus_iri,
                RDF.type,
            )
        ))
        _sorted_types = sorted(_types, key=_type_sortkey, reverse=True)
        if not _sorted_types:
            return None
        return self._format_typename(_sorted_types[0].name)

    def _type_list(self, focus_iri):
        return [
            self._format_type_iri(_type_iri)
            for _type_iri in gather.objects_by_pathset(
                self.tripledict,
                focus_iri,
                RDF.type,
            )
        ]

    def _format_type_iri(self, focus_iri):
        if focus_iri in SHAREv2:
            _typename = gather.IriNamespace.without_namespace(focus_iri, namespace=SHAREv2)
        elif focus_iri in OSFMAP:
            _typename = gather.IriNamespace.without_namespace(focus_iri, namespace=OSFMAP)
        else:
            return focus_iri  # oh well
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


def _obj_to_string_or_none(obj):
    if obj is None:
        return None
    if isinstance(obj, gather.Text):
        return obj.unicode_text
    return str(obj)
