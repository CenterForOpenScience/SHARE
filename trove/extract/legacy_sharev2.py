import datetime
import typing

from django.conf import settings
from gather import primitive_rdf, gathering

from share.util.graph import MutableNode
from share.regulate import Regulator
from trove.vocab.namespaces import OSFMAP, DCTERMS, FOAF, DCAT, SHAREv2
from trove.vocab.osfmap import OSFMAP_NORMS
from ._base import BaseRdfExtractor


class LegacySharev2Extractor(BaseRdfExtractor):
    # side-effected by extract_rdf (to support back-compat shenanigans)
    extracted_focus_iri: typing.Optional[str] = None
    sharev2graph_centralnode: typing.Optional[MutableNode] = None

    def extract_rdf(self, input_document):
        _transformer = self.source_config.get_transformer()
        _sharev2graph = _transformer.transform(input_document)
        if _sharev2graph:  # in-place update
            Regulator(source_config=self.source_config).regulate(_sharev2graph)
        self.sharev2graph_centralnode = _sharev2graph.get_central_node(guess=True)
        _central_focus = _focus_for_mnode(self.sharev2graph_centralnode)
        self.extracted_focus_iri = _choose_iri(_central_focus.iris)
        _gathering = osfmap_from_normd.new_gathering({
            'source_config': self.source_config,
            'mnode': None,  # provided by focus
        })
        _gathering.ask_all_about(_central_focus)
        return _gathering.leaf_a_record()


###
# gathering OSFMAP-ish RDF from SHAREv2 NormalizedData

osfmap_from_normd = gathering.GatheringOrganizer(
    namestory=(
        primitive_rdf.text('sharev2-normd'),
    ),
    norms=OSFMAP_NORMS,
    gatherer_kwargnames={'mnode', 'source_config'},
)


# gatherers:

@osfmap_from_normd.gatherer(focustype_iris={
    SHAREv2.AbstractCreativeWork,
})
def _gather_work(focus, *, mnode, source_config):
    for _iri in focus.iris:
        yield (DCTERMS.identifier, primitive_rdf.text(_iri))
    _language_tag = mnode['language']
    _language_iri = (
        primitive_rdf.IANA_LANGUAGE[_language_tag]
        if _language_tag
        else None
    )
    yield (DCTERMS.title, primitive_rdf.text(mnode['title'], language_iri=_language_iri))
    yield (DCTERMS.description, primitive_rdf.text(mnode['description'], language_iri=_language_iri))
    yield (DCTERMS.created, _date_or_none(mnode['date_published']))
    yield (DCTERMS.modified, _date_or_none(mnode['date_updated']))
    yield (DCTERMS.date, _date_or_none(mnode['date_published'] or mnode['date_updated']))
    yield (DCTERMS.rights, primitive_rdf.text(mnode['free_to_read_type']))
    yield (DCTERMS.available, primitive_rdf.text(mnode['free_to_read_date']))
    yield (DCTERMS.rights, primitive_rdf.text(mnode['rights']))
    yield (DCTERMS.language, primitive_rdf.text(_language_tag))
    yield (OSFMAP.registration_type, primitive_rdf.text(mnode['registration_type']))  # TODO: not in OSFMAP
    yield (OSFMAP.dateWithdrawn, primitive_rdf.text(mnode['withdrawn']))  # TODO: is boolean, not date
    yield (OSFMAP.withdrawalJustification, primitive_rdf.text(mnode['justification']))  # TODO: not in OSFMAP
    for _subject in mnode['subjects']:
        yield (DCTERMS.subject, primitive_rdf.text(_subject['name']))  # TODO: iri? lineage?
    for _tag in mnode['tags']:
        yield (OSFMAP.keyword, primitive_rdf.text(_tag['name']))
    for _agent_relation in mnode['agent_relations']:
        yield (
            _agentwork_relation_iri(_agent_relation),
            _focus_for_mnode(_agent_relation['agent']),
        )
    for _work_relation in mnode['outgoing_creative_work_relations']:
        yield (
            _workwork_relation_iri(_work_relation),
            _focus_for_mnode(_work_relation['related']),
        )
    for _work_relation in mnode['incoming_creative_work_relations']:
        yield (
            _focus_for_mnode(_work_relation['subject']),
            _workwork_relation_iri(_work_relation),
            focus,
        )


@osfmap_from_normd.gatherer(DCTERMS.subject, focustype_iris={
    SHAREv2.AbstractCreativeWork,
})
def _gather_work_subjects(focus, *, mnode, source_config):
    _source_name = source_config.source.long_title
    for _thru_subject_mnode in mnode['subject_relations']:
        _subject_mnode = _thru_subject_mnode['subject']
        if not (_thru_subject_mnode['is_deleted'] or _subject_mnode['is_deleted']):
            yield (DCTERMS.subject, _subject_mnode['name'])
            yield (DCTERMS.subject, _serialize_subject(_subject_mnode, _source_name))
            _synonym_mnode = _subject_mnode['central_synonym']
            if _synonym_mnode and not _synonym_mnode['is_deleted']:
                yield (DCTERMS.subject, _synonym_mnode['name'])
                yield (DCTERMS.subject, _serialize_subject(_synonym_mnode, _source_name))


@osfmap_from_normd.gatherer(focustype_iris={
    SHAREv2.AbstractAgent,
})
def _gather_agent(focus, *, mnode, source_config):
    for _iri in focus.iris:
        if not _iri.startswith('_:'):  # HACK: non-blank blank node (stop that)
            yield (DCTERMS.identifier, primitive_rdf.text(_iri))
    if 'Person' in mnode.schema_type.type_lineage:
        yield (DCTERMS.type, FOAF.Person)
    if 'Organization' in mnode.schema_type.type_lineage:
        yield (DCTERMS.type, FOAF.Organization)
    yield (FOAF.name, primitive_rdf.text(mnode['name']))
    for _agent_relation in mnode['outgoing_agent_relations']:
        yield (
            OSFMAP.affiliation,
            _focus_for_mnode(_agent_relation['related']),
        )
    for _agent_relation in mnode['incoming_agent_relations']:
        yield (
            _focus_for_mnode(_agent_relation['subject']),
            OSFMAP.affiliation,
            focus,
        )


# helpers:

def _iris_for_mnode(mnode: MutableNode) -> typing.Iterable[str]:
    _identifiers = set(mnode['identifiers'])
    if _identifiers:
        for _identifier in _identifiers:
            yield _identifier['uri']
    elif mnode.id.startswith('_:'):
        yield f'blank{mnode.id[1:]}'


def _choose_iri(iris):
    return sorted(iris, key=len)[0]


def _focus_for_mnode(mnode: MutableNode):
    return gathering.focus(
        frozenset(_iris_for_mnode(mnode)),
        frozenset(_focustype_iris(mnode)),
        {'mnode': mnode},
    )


def _has_parent(mnode: MutableNode) -> bool:
    return any(
        relation_node.type == 'ispartof'
        for relation_node in mnode['outgoing_creative_work_relations']
    )


def _date_or_none(maybe_date) -> typing.Optional[datetime.date]:
    if isinstance(maybe_date, str):
        _datetime = datetime.datetime.fromisoformat(maybe_date)
        return _datetime.date()
    if isinstance(maybe_date, datetime.datetime):
        return maybe_date.date()
    if isinstance(maybe_date, datetime.date):
        return maybe_date
    if maybe_date is None:
        return None
    raise ValueError(f'expected datetime.date, str, or None (got {maybe_date})')


def _focustype_iris(mnode: MutableNode) -> typing.Iterable[str]:
    _typenames = {
        mnode.schema_type.name,
        mnode.schema_type.concrete_type,
        *mnode.schema_type.type_lineage,
    }
    for _typename in _typenames:
        yield SHAREv2[_typename]
    if 'Preprint' in _typenames:
        yield OSFMAP.Preprint
    if 'Project' in _typenames:
        if _has_parent(mnode):
            yield OSFMAP.ProjectComponent
        else:
            yield OSFMAP.Project
    if 'Registration' in _typenames:
        if _has_parent(mnode):
            yield OSFMAP.RegistrationComponent
        else:
            yield OSFMAP.Registration
    if 'AbstractAgent' in _typenames:
        yield OSFMAP.Agent


def _agentwork_relation_iri(agentwork_relation: MutableNode):
    _sharev2_relation_types = set(agentwork_relation.schema_type.type_lineage)
    if 'Creator' in _sharev2_relation_types:
        return DCTERMS.creator
    if 'Contributor' in _sharev2_relation_types:
        return DCTERMS.contributor
    if 'Funder' in _sharev2_relation_types:
        return OSFMAP.funder  # TODO: different kind of osfmap expression
    if 'Publisher' in _sharev2_relation_types:
        return DCTERMS.publisher
    if 'Host' in _sharev2_relation_types:
        return DCAT.accessService
    # generic AgentWorkRelation
    _sharev2_agent_types = set(agentwork_relation['agent'].schema_type.type_lineage)
    if 'Organization' in _sharev2_agent_types:
        return OSFMAP.affiliation
    return DCTERMS.contributor


WORKWORK_RELATION_MAP = {
    'cites': DCTERMS.references,
    'compiles': DCTERMS.references,
    'corrects': DCTERMS.references,
    'discusses': DCTERMS.references,
    'disputes': DCTERMS.references,
    'documents': DCTERMS.references,
    'extends': DCTERMS.references,
    'isderivedfrom': DCTERMS.references,
    'ispartof': DCTERMS.isPartOf,
    'issupplementto': OSFMAP.supplements,
    'references': DCTERMS.references,
    'repliesto': DCTERMS.references,
    'retracts': DCTERMS.references,
    'reviews': DCTERMS.references,
    'usesdatafrom': DCTERMS.references,
}


def _workwork_relation_iri(workwork_relation: MutableNode):
    try:
        return WORKWORK_RELATION_MAP[workwork_relation.type]
    except KeyError:
        return DCTERMS.relation


def _serialize_subject(subject_node: MutableNode, source_name=None):
    '''a specific serialization of a subject, for backcompat with questionable decisions
    '''
    _subject_lineage = [subject_node['name']]
    _next_subject = subject_node['parent']
    while _next_subject:
        _subject_lineage.insert(0, _next_subject['name'])
        _next_subject = _next_subject['parent']
    _taxonomy_name = (
        source_name
        if source_name and subject_node['central_synonym']
        else settings.SUBJECTS_CENTRAL_TAXONOMY
    )
    _subject_lineage.insert(0, _taxonomy_name)
    return '|'.join(_subject_lineage)
