import json
import typing

from gather import (
    focus,
    text,
    twopledict_as_jsonld,
    IANA_LANGUAGE,
    GatheringOrganizer,
)

from share.schema.osfmap import (
    osfmap_labeler,
    OSFMAP_NORMS,
    DCTERMS,
    FOAF,
    OSFMAP,
    FULL_DATE,
)
from share.util.rdfutil import SHAREv2
from share.util.graph import MutableGraph, MutableNode
from .base import MetadataFormatter


class OsfmapJsonldFormatter(MetadataFormatter):
    def format(self, normalized_data) -> typing.Optional[str]:
        _mgraph = MutableGraph.from_jsonld(normalized_data.data)
        _central_node = _mgraph.get_central_node(guess=True)
        _central_focus = _focus_for_mnode(_central_node)
        _gathering = osfmap_from_normd.new_gathering({
            'normd': normalized_data,
            'mnode': None,  # provided by focus
        })
        _gathering.ask_all_about(_central_focus)
        _tripledict = _gathering.leaf_a_record()
        _jsondict = twopledict_as_jsonld(
            _tripledict[_central_focus.single_iri()],
            OSFMAP_NORMS.vocabulary,
            osfmap_labeler.all_labels_by_iri(),
        )
        return json.dumps(_jsondict)


###
# gathering OSFMAP from SHAREv2 NormalizedData

osfmap_from_normd = GatheringOrganizer(
    namestory=(
        text('sharev2-normd', language_iris=()),
    ),
    norms=OSFMAP_NORMS,
    gatherer_kwargnames={'mnode', 'normd'},
)


# gatherers:

@osfmap_from_normd.gatherer(focustype_iris={
    SHAREv2.abstractcreativework,
})
def _gather_work(focus, *, normd, mnode):
    for _iri in focus.iris:
        yield (DCTERMS.identifier, text(_iri, language_iris=()))
    _language_tag = mnode['language']
    _language_iris = (
        {IANA_LANGUAGE[_language_tag]}
        if _language_tag
        else ()
    )
    yield (DCTERMS.title, text(mnode['title'], language_iris=_language_iris))
    yield (DCTERMS.description, text(mnode['_description'], language_iris=_language_iris))
    yield (DCTERMS.created, text(mnode['date_published'], language_iris=FULL_DATE))
    yield (DCTERMS.modified, text(mnode['date_updated'], language_iris=FULL_DATE))
    yield (DCTERMS.date, text((
        mnode['date_published']
        or mnode['date_updated']
        or normd.created_at.isoformat()
    ), language_iris=FULL_DATE))
    yield (DCTERMS.rights, text(mnode['free_to_read_type'], language_iris=()))
    yield (DCTERMS.available, text(mnode['free_to_read_date'], language_iris=()))
    yield (DCTERMS.rights, text(mnode['rights'], language_iris=()))
    yield (DCTERMS.language, text(_language_tag, language_iris=()))
    yield (OSFMAP.registration_form, text(mnode['registration_form'], language_iris=()))  # TODO: not in OSFMAP
    yield (OSFMAP.dateWithdrawn, text(mnode['withdrawn'], language_iris=()))  # TODO: is boolean, not date
    yield (OSFMAP.withdrawalJustification, text(mnode['justification'], language_iris=()))  # TODO: not in OSFMAP
    for _subject in mnode['subjects']:
        yield (OSFMAP.subject, text(_subject['name'], language_iris=()))  # TODO: iri? lineage?
    for _tag in mnode['tags']:
        yield (OSFMAP.keyword, text(_tag['name'], language_iris=()))
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


@osfmap_from_normd.gatherer(focustype_iris={
    SHAREv2.abstractagent,
})
def _gather_agent(focus, *, normd, mnode):
    for _iri in focus.iris:
        yield (DCTERMS.identifier, text(_iri, language_iris=()))
    if SHAREv2.person in mnode.schema_type.type_lineage:
        yield (DCTERMS.type, FOAF.Person)
    if SHAREv2.organization in mnode.schema_type.type_lineage:
        yield (DCTERMS.type, FOAF.Organization)
    yield (FOAF.name, text(mnode['name'], language_iris=()))
    yield (SHAREv2.location, text(mnode['location'], language_iris=()))
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
    if mnode is None:
        breakpoint()
    _identifiers = set(mnode['identifiers'])
    if _identifiers:
        for _identifier in _identifiers:
            yield _identifier['uri']
    else:
        yield mnode.id


def _focus_for_mnode(mnode: MutableNode):
    return focus(
        frozenset(_iris_for_mnode(mnode)),
        frozenset(_focustype_iris(mnode)),
        {'mnode': mnode},
    )


def _has_parent(mnode: MutableNode) -> bool:
    return any(
        relation_node.type == 'ispartof'
        for relation_node in mnode['outgoing_creative_work_relations']
    )


def _focustype_iris(mnode: MutableNode) -> typing.Iterable[str]:
    _sharev2_type = mnode.type
    _sharev2_concrete_type = mnode.concrete_type
    yield SHAREv2[_sharev2_type]
    yield SHAREv2[_sharev2_concrete_type]
    if _sharev2_concrete_type == 'abstractcreativework':
        if _sharev2_type == 'preprint':
            yield OSFMAP.Preprint
        if _sharev2_type == 'project':
            if _has_parent(mnode):
                yield OSFMAP.ProjectComponent
            else:
                yield OSFMAP.Project
        if _sharev2_type == 'registration':
            if _has_parent(mnode):
                yield OSFMAP.RegistrationComponent
            else:
                yield OSFMAP.Registration
    if _sharev2_concrete_type == 'abstractagent':
        yield OSFMAP.Agent


def _agentwork_relation_iri(agentwork_relation: MutableNode):
    _sharev2_types = set(agentwork_relation.schema_type.type_lineage)
    if 'creator' in _sharev2_types:
        return DCTERMS.creator
    if 'funder' in _sharev2_types:
        return OSFMAP.funder  # TODO: different kind of osfmap expression
    if ('publisher' in _sharev2_types) or ('host' in _sharev2_types):
        return DCTERMS.publisher
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
