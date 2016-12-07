import pytest
import json
import re

from share.change import ChangeGraph
from share.models import ChangeSet
from share.util import IDObfuscator

from tests.share.models.factories import NormalizedDataFactory
from tests.share.normalize.factories import *


def camelCase_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

initial = [
    Preprint(
        id=1,
        identifiers=[WorkIdentifier(1, id=1)],
        agent_relations=[
            Contributor(agent=Organization(id=1, name='American Heart Association')),
            Creator(agent=Organization(2, id=2)),
            Creator(agent=Organization(id=3)),

        ]
    ),
    CreativeWork(
        id=2,
        identifiers=[WorkIdentifier(id=2)],
        agent_relations=[
            Creator(agent=Person(1, identifiers=[AgentIdentifier(14)])),
            Funder(agent=Institution(id=5, name='NIH')),
            Publisher(agent=Institution(id=6)),
        ],
        related_works=[
            Publication(
                11,
                id=11,
                agent_relations=[
                    Contributor(id=12, agent=Institution(id=7, name="Test University"))
                ],
                identifiers=[WorkIdentifier(id=3)]
            )
        ]
    )
]


@pytest.mark.django_db
class TestGeneratedEndpoints:

    @pytest.mark.parametrize('generator, route, controlled_values', [
        ([Institution(id=5, name='NIH')], 'institution', ['name']),
        ([Organization(2, id=2)], 'organization', ['name']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(id=2)],
            agent_relations=[Funder(agent=Institution(id=5, name='NIH'))]
        )], 'funder', ['citedAs']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(id=2)],
            related_works=[
                Publication(11, id=11, identifiers=[WorkIdentifier(id=3)])
            ]
        )], 'publication', ['title', 'description']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(id=2)],
            agent_relations=[Creator(agent=Person(1, identifiers=[AgentIdentifier(14)]))]
        )], 'person', ['name']),
    ])
    def test_get_data(self, generator, route, controlled_values, client, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process(disambiguate=False)
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        cg = ChangeGraph(Graph(*generator))
        cg.process()

        for obj in cg.serialize():
            if obj['@type'] == route:
                expected_id = obj['@id']
                expected = obj

        response = client.get('/api/v2/{}/{}/'.format(route, expected_id))

        actual = json.loads(response.content.decode(encoding='UTF-8'))

        assert response.status_code == 200
        assert actual['data']['id'] == str(IDObfuscator.decode_id(expected_id))
        assert actual['data']['attributes']['type'] == expected['@type']
        for value in controlled_values:
            assert actual['data']['attributes'][value] == expected[camelCase_to_underscore(value)]
