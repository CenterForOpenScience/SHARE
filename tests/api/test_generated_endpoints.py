import pytest

from share.change import ChangeGraph
from share.models import ChangeSet
from share.util import IDObfuscator

from tests.share.models.factories import NormalizedDataFactory
from tests.share.normalize.factories import *

initial = [
    Preprint(
        id=3,
        identifiers=[WorkIdentifier(1, id=1)],
        agent_relations=[
            Contributor(agent=Organization(id=1, name='American Heart Association')),
            Creator(agent=Organization(id=2)),
            Creator(agent=Organization(id=3)),

        ]
    ),
    CreativeWork(
        id=2,
        identifiers=[WorkIdentifier(id=2)],
        agent_relations=[
            Creator(agent=Organization(id=4)),
            Funder(agent=Institution(id=5, name='NIH')),
            Publisher(agent=Institution(id=6)),
        ],
        related_works=[
            Patent(
                id=3,
                agent_relations=[
                    Contributor(agent=Institution(id=7))
                ],
                identifiers=[WorkIdentifier(id=3)]
            )
        ]
    )
]


@pytest.mark.django_db
class TestGeneratedEndpoints:

    @pytest.mark.parametrize('expected, route', [
        #
        ([Institution(id=5, name='NIH')], 'institution'),
        #
        ([Organization(2)], 'organization'),
        #
        ([Publication(related_agents=[Institution(4)])], 'publication'),
        #
        ([Publication(related_agents=[Consortium(name='COS')])], 'consortium'),
        #
        ([Preprint(related_agents=[Institution(8)])], 'creativework'),
        #
        ([CreativeWork(related_agents=[Organization(name='Bill Gates')])], 'funder'),
    ])
    def test_get_data(self, expected, route, client, Graph):
        initial_cg = ChangeGraph(Graph(*initial))
        initial_cg.process(disambiguate=False)
        ChangeSet.objects.from_graph(initial_cg, NormalizedDataFactory().id).accept()

        cg = ChangeGraph(Graph(*expected))
        cg.process()
        expected_id = IDObfuscator.decode_id(cg.serialize()[0]['@id'])

        # assert serializer gives what is generated
        # second change graph and move around things
        # assert controlled values are there (parameter)
        # dictionary of model keys
        # should use the encoded pk
        # cg.serialize()
        # cg.lookup(id, type).serialize()

        response = client.get('/api/v2/{}/{}'.format(route, expected_id))

        assert response.status_code == 200
        assert response.content == expected
