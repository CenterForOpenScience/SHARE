import pytest

from share import models

from tests.share.normalize.factories import *


initial = [
    Preprint(
        identifiers=[WorkIdentifier(1)],
        agent_relations=[
            Contributor(cited_as='B. Dylan', agent=Person(1, identifiers=[AgentIdentifier(1)], name='Bob Dylan')),
            Contributor(cited_as='AHA', agent=Organization(1, identifiers=[AgentIdentifier(2)], name='American Heart Association')),
            Creator(cited_as='COS', agent=Organization(2, identifiers=[AgentIdentifier(3)], name='COS')),
            AgentWorkRelation(cited_as='Science Guy', agent=Organization(4, identifiers=[AgentIdentifier(4)], name='Science Guy')),
        ]
    ),
    CreativeWork(
        identifiers=[WorkIdentifier(2)],
        agent_relations=[
            Funder(cited_as='Bill Gates', agent=Person(name='Bill R. Gates', identifiers=[AgentIdentifier(5)])),
            AgentWorkRelation(cited_as='Bill Nye', agent=Person(4, identifiers=[AgentIdentifier(6)], name='Bill Nye')),
            Funder(cited_as='NIH', agent=Institution(5, name='National Institute of Health', identifiers=[AgentIdentifier(7)]))
        ]
    ),
    Publication(
        identifiers=[WorkIdentifier(3)],
        agent_relations=[
            Creator(cited_as='G. Washington', agent=Person(5, identifiers=[AgentIdentifier(8)], name='George Washington')),
            Creator(agent=Organization(7))
        ],
        related_works=[
            Patent(
                agent_relations=[
                    Contributor(cited_as='T.J.', agent=Person(8, identifiers=[AgentIdentifier(9)], name='Thomas Jefferson')),
                    Contributor(agent=Institution(8))
                ],
                identifiers=[WorkIdentifier(4)]
            )
        ]
    ),
]


@pytest.mark.django_db
class TestAgentRelationDisambiguation:

    @pytest.fixture
    def ingest_initial(self, Graph, ingest):
        ingest(Graph(initial))

    @pytest.mark.parametrize('input, model_delta', [
        # different name, same cited as, no work, person doesn't match
        (
            [Person(name='B. Dylan')],
            {models.Person: 1}
        ),
        # different name, same cited as, no work, agent doesn't match
        (
            [Institution(name='NIH')],
            {models.Institution: 1}
        ),
        # person with same cited as, different relation, on a different work doesn't match
        (
            [CreativeWork(agent_relations=[Host(cited_as='Bill Gates', agent=Person(name='Bill Gates'))])],
            {models.Person: 1}
        ),
        # agent with same cited as, different relation, on a different work doesn't match
        (
            [CreativeWork(agent_relations=[Host(cited_as='AHA', agent=Organization(name='AHA'))])],
            {models.Organization: 1}
        ),
        # person with same cited as, same relation, on a different work doesn't match
        (
            [CreativeWork(agent_relations=[Funder(cited_as='Bill Gates', agent=Person(name='Bill Gates'))])],
            {models.Person: 1}
        ),
        # agent with same cited as, same relation, on a different work doesn't match
        (
            [CreativeWork(agent_relations=[Funder(cited_as='NIH', agent=Institution(name='NIH'))])],
            {models.Institution: 1}
        ),
        # longer cited as or alphabetical, same work, same person, same relation, different cited_as
        (
            [Publication(identifiers=[WorkIdentifier(3)], agent_relations=[Creator(cited_as='George Washington', agent=Person(5, identifiers=[AgentIdentifier(8)], name='George Washington'))])],
            {models.Person: 0, models.Creator: 0}
        ),
        # longer cited as or alphabetical, same work, same agent, same relation, different cited_as
        (
            [CreativeWork(identifiers=[WorkIdentifier(2)], agent_relations=[Funder(cited_as='National Institute of Health', agent=Institution(5, name='National Institute of Health', identifiers=[AgentIdentifier(7)]))])],
            {models.Institution: 0, models.Funder: 0}
        ),

        # Specified class should win (Contributor/Creator) person (Unique to Contributors)
        (
            [Publication(identifiers=[WorkIdentifier(3)], agent_relations=[Contributor(cited_as='George Washington', agent=Person(5, identifiers=[AgentIdentifier(8)], name='George Washington'))])],
            {models.Person: 0, models.Contributor: 1, models.Creator: -1}
        ),
        (
            [Patent(identifiers=[WorkIdentifier(4)], agent_relations=[Creator(cited_as='Thomas Jefferson', agent=Person(8, identifiers=[AgentIdentifier(9)], name='Thomas Jefferson'))])],
            {models.Person: 0, models.Creator: 1, models.Contributor: -1}
        ),

        # Specified class should win (Contributor/Creator) person (Unique to Contributors)
        (
            [Preprint(identifiers=[WorkIdentifier(1)], agent_relations=[Contributor(cited_as='COS', agent=Organization(2, identifiers=[AgentIdentifier(3)], name='COS'))])],
            {models.Organization: 0, models.Contributor: 1, models.Creator: -1}
        ),
        (
            [Preprint(identifiers=[WorkIdentifier(1)], agent_relations=[Creator(cited_as='AHA', agent=Organization(1, identifiers=[AgentIdentifier(2)], name='American Heart Association'))])],
            {models.Organization: 0, models.Creator: 1, models.Contributor: -1}
        ),

        # sub class should win (AgentWorkRelation/Funder) person
        (
            [CreativeWork(identifiers=[WorkIdentifier(2)], agent_relations=[AgentWorkRelation(cited_as='Bill Gates', agent=Person(name='Bill R. Gates', identifiers=[AgentIdentifier(5)]))])],
            {models.Person: 0, models.AgentWorkRelation: 0}
        ),
        (
            [CreativeWork(identifiers=[WorkIdentifier(2)], agent_relations=[Funder(cited_as='Bill Nye', agent=Person(4, identifiers=[AgentIdentifier(6)], name='Bill Nye'))])],
            {models.Person: 0, models.Funder: 1, models.AgentWorkRelation: -1}
        ),

        # sub class should win (AgentWorkRelation/Funder) agent
        (
            [CreativeWork(identifiers=[WorkIdentifier(2)], agent_relations=[AgentWorkRelation(cited_as='NIH', agent=Institution(5, name='National Institute of Health', identifiers=[AgentIdentifier(7)]))])],
            {models.Institution: 0, models.AgentWorkRelation: 0}
        ),
        (
            [Preprint(identifiers=[WorkIdentifier(1)], agent_relations=[Funder(cited_as='Science Guy', agent=Organization(4, identifiers=[AgentIdentifier(4)], name='Science Guy'))])],
            {models.Institution: 0, models.Funder: 1, models.AgentWorkRelation: -1}
        ),

        # sub class should win (AgentWorkRelation/Creator) person
        (
            [Publication(identifiers=[WorkIdentifier(3)], agent_relations=[AgentWorkRelation(cited_as='G. Washington', agent=Person(5, identifiers=[AgentIdentifier(8)], name='George Washington'))])],
            {models.Person: 0, models.AgentWorkRelation: 0}
        ),
        (
            [CreativeWork(identifiers=[WorkIdentifier(2)], agent_relations=[Creator(cited_as='Bill Nye', agent=Person(4, identifiers=[AgentIdentifier(6)], name='Bill Nye'))])],
            {models.Person: 0, models.Creator: 1, models.AgentWorkRelation: -1}
        ),

        # sub class should win (AgentWorkRelation/Creator) agent
        (
            [Preprint(identifiers=[WorkIdentifier(1)], agent_relations=[AgentWorkRelation(cited_as='COS', agent=Organization(2, identifiers=[AgentIdentifier(3)], name='COS'))])],
            {models.Organization: 0, models.AgentWorkRelation: 0}
        ),
        (
            [Preprint(identifiers=[WorkIdentifier(1)], agent_relations=[Creator(cited_as='Science Guy', agent=Organization(4, identifiers=[AgentIdentifier(4)], name='Science Guy'))])],
            {models.Organization: 0, models.Creator: 1, models.AgentWorkRelation: -1}
        ),
    ])
    def test_disambiguate(self, input, ingest_initial, ingest, model_delta, Graph):
        Graph.reseed()
        before_count = {}
        for model in model_delta.keys():
            before_count[model] = model.objects.filter(type=model._meta.label_lower).count()

        ingest(Graph(input))

        for model in model_delta.keys():
            assert model.objects.filter(type=model._meta.label_lower).count() - before_count[model] == model_delta[model]

    def test_no_changes(self, ingest_initial, ingest, Graph):
        Graph.discarded_ids.clear()
        cs = ingest(Graph(initial))
        assert cs is None
