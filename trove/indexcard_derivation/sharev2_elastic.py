import json
import re

from django.conf import settings
import gather

from share.schema.osfmap import DCTERMS
from share.util.names import get_related_agent_name
from share.util import IDObfuscator
from share import models as share_db
from trove import models as trove_db

from ._base import IndexcardDerivation


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


class ShareV2ElasticDerivation(IndexcardDerivation):
    __tripledict = None

    def derive_indexcard(self, rdf_indexcard: trove_db.RdfIndexcard):
        try:
            _suid = rdf_indexcard.get_backcompat_sharev2_suid()
        except share_db.SourceUniqueIdentifier.DoesNotExist:
            _suid = rdf_indexcard.get_suid()
        _tripledict = rdf_indexcard.as_rdf_tripledict()
        _focus_iri = rdf_indexcard.focus_iri
        _focus_twopledict = _tripledict[_focus_iri]
        _source_name = _suid.source_config.source.long_title
        _derived_sharev2 = {
            ###
            # metadata about the record/indexcard in this system
            'id': IDObfuscator.encode(_suid),
            'date_created': _suid.created.isoformat(),
            'date_modified': rdf_indexcard.modified.isoformat(),
            'sources': [_source_name],
            'source_config': _suid.source_config.label,
            'source_unique_id': _suid.identifier,
            ###
            # metadata about a resource in whichever other system
            'type': _single_type(_focus_twopledict),
            'types': [
                _format_type(_type)
                for _type in _focus_twopledict.get(gather.RDF.type, ())
            ],
            'date_published': _single_value(_focus_twopledict, [
                DCTERMS.created,
                DCTERMS.date,
            ]),
            'date_updated': _single_value(_focus_twopledict, [
                DCTERMS.modified,
                DCTERMS.date,
            ]),
            'description': _single_value(_focus_twopledict, DCTERMS.description),
            'justification': _single_value(_focus_twopledict, OSFMAP.withdrawalJustification),
            'language': _single_value(_focus_twopledict, DCTERMS.language),
            'registration_type': _single_value(_focus_twopledict, OSFMAP.registration_type),
            'retracted': bool(_single_value(_focus_twopledict, OSFMAP.dateWithdrawn)),
            'title': _single_value(_focus_twopledict, DCTERMS.title),
            'withdrawn': _single_value(_focus_twopledict, OSFMAP.dateWithdrawn),
            'date': _single_value(_focus_twopledict, [
                DCTERMS.date,
                DCTERMS.created,
                DCTERMS.modified,
            ]),
            # related names:
            'affiliations': _related_names(_tripledict, _focus_iri, [
                OSFMAP.affiliatedInstitution
            ]),
            'contributors': _related_names(_tripledict, _focus_iri, [
                DCTERMS.contributor,
                DCTERMS.creator,
            ]),
            'funders': _related_names(_tripledict, _focus_iri, [
                OSFMAP.funder,
            ]),
            'publishers': _related_names(_tripledict, _focus_iri, [
                DCTERMS.publisher,
            ]),
            'hosts': _related_names(_tripledict, _focus_iri, [

            ]),

            # other relations:
            'identifiers': [
                identifier_node['uri']
                for identifier_node in central_work['identifiers']
            ],
            'tags': [
                tag_node['name']
                for tag_node in central_work['tags']
            ],
            'subjects': self._get_subjects(central_work, source_name),
            'subject_synonyms': self._get_subject_synonyms(central_work),

            # osf-specific extra
            'osf_related_resource_types': (central_work['extra'] or {}).get('osf_related_resource_types'),

            # a bunch of nested data because reasons -- used mostly for rendering search results
            'lists': {
                'affiliations': self._build_related_agent_list(central_work, ['agentworkrelation']),
                'contributors': self._build_related_agent_list(central_work, [
                    'contributor',
                    'creator',
                    'principalinvestigator',
                    'principalinvestigatorcontact',
                ]),
                'funders': self._build_related_agent_list(central_work, ['funder']),
                'publishers': self._build_related_agent_list(central_work, ['publisher']),
                'hosts': self._build_related_agent_list(central_work, ['host']),
                'lineage': self._build_work_lineage(central_work),
            },
        }
        return json.dumps(strip_empty_values(_derived_sharev2))


    def _get_related_agent_names(self, work_node, relation_types):
        return [
            get_related_agent_name(relation_node)
            for relation_node in work_node['agent_relations']
            if relation_node.type in relation_types
        ]

    def _get_subjects(self, work_node, source_name):
        return [
            self._serialize_subject(through_subject['subject'], source_name)
            for through_subject in work_node['subject_relations']
            if (
                not through_subject['is_deleted']
                and not through_subject['subject']['is_deleted']
            )
        ]

    def _get_subject_synonyms(self, work_node):
        return [
            self._serialize_subject(through_subject['subject']['central_synonym'])
            for through_subject in work_node['subject_relations']
            if (
                not through_subject['is_deleted']
                and not through_subject['subject']['is_deleted']
                and through_subject['subject']['central_synonym']
            )
        ]

    def _serialize_subject(self, subject_node, source_name=None):
        subject_lineage = [subject_node['name']]
        next_subject = subject_node['parent']
        while next_subject:
            subject_lineage.insert(0, next_subject['name'])
            next_subject = next_subject['parent']

        if source_name and subject_node['central_synonym']:
            taxonomy_name = source_name
        else:
            taxonomy_name = settings.SUBJECTS_CENTRAL_TAXONOMY

        subject_lineage.insert(0, taxonomy_name)
        return '|'.join(subject_lineage)

    def _build_list_agent(self, relation_node):
        agent_node = relation_node['agent']
        return {
            'type': format_node_type(agent_node),
            'types': format_node_type_lineage(agent_node),
            'name': agent_node['name'] or get_related_agent_name(relation_node),
            'given_name': agent_node['given_name'],
            'family_name': agent_node['family_name'],
            'additional_name': agent_node['additional_name'],
            'suffix': agent_node['suffix'],
            'identifiers': [
                identifier_node['uri']
                for identifier_node in agent_node['identifiers']
            ],
            'relation': format_node_type(relation_node),
            'order_cited': relation_node['order_cited'],
            'cited_as': relation_node['cited_as'],
        }

    def _build_related_agent_list(self, work_node, relation_types):
        return [
            self._build_list_agent(relation_node)
            for relation_node in work_node['agent_relations']
            if relation_node.type in relation_types
        ]

    def _build_work_lineage(self, work_node):
        try:
            parent_work = next(
                relation_node['related']
                for relation_node in work_node['outgoing_creative_work_relations']
                if relation_node.type == 'ispartof'
            )
        except StopIteration:
            return ()

        parent_lineage = self._build_work_lineage(parent_work)
        parent_data = {
            'type': format_node_type(parent_work),
            'types': format_node_type_lineage(parent_work),
            'title': parent_work['title'],
            'identifiers': [
                identifier_node['uri']
                for identifier_node in parent_work['identifiers']
            ],
        }
        return (
            *parent_lineage,
            parent_data,
        )


def _format_type(type_iri):
    # convert from PascalCase to lower case with spaces between words
    return re.sub(r'\B([A-Z])', r' \1', type_name).lower()


def _single_value(twopledict, predicate_iri_or_iris):
    # for sharev2 back-compat, some fields must have a single value
    # (tho now the corresponding rdf property may have many values)
    _predicate_iris = (
        [predicate_iri_or_iris]
        if isinstance(predicate_iri_or_iris, str)
        else predicate_iri_or_iris
    )
    for _pred in _predicate_iris:
        _obj_set = twopledict.get(_pred)
        if _obj_set:
            return next(iter(_obj_set))
    return None


def _related_names(tripledict, focus_iri, predicate_iris):
    for _predicate_iri in predicate_iris:
        _related_iris = tripledict.get(focus_iri, {}).get(_predicate_iri, ())
        for _iri in _related_iris:
            yield from tripledict.get(_iri, {}).get(FOAF.name, ())
