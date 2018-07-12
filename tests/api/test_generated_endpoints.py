import pytest
import json
import re

from share.disambiguation import GraphDisambiguator
from share.regulate import Regulator
from share.util import IDObfuscator

from tests import factories
from tests.share.normalize.factories import *


def camelCase_to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


initial = [
    Preprint(
        id=1,
        is_deleted=False,
        identifiers=[WorkIdentifier(1, id=1)],
        agent_relations=[
            Contributor(agent=Organization(id=1, name='American Heart Association')),
            Creator(agent=Organization(2, id=2)),
            Creator(agent=Organization(id=3)),

        ]
    ),
    CreativeWork(
        id=2,
        identifiers=[WorkIdentifier(2, id=2)],
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
                identifiers=[WorkIdentifier(3, id=3)]
            )
        ]
    )
]


@pytest.mark.django_db
class TestGeneratedEndpoints:

    @pytest.mark.parametrize('generator, model, route, controlled_values', [
        ([Institution(id=5, name='NIH')], 'institution', 'institutions', ['name']),
        ([Organization(2, id=2)], 'organization', 'organizations', ['name']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(2, id=2)],
            agent_relations=[Funder(agent=Institution(id=5, name='NIH'))]
        )], 'funder', 'funders', ['citedAs']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(2, id=2)],
            related_works=[
                Publication(11, id=11, identifiers=[WorkIdentifier(3, id=3)])
            ]
        )], 'publication', 'publications', ['title', 'description']),
        ([CreativeWork(
            id=2,
            identifiers=[WorkIdentifier(2, id=2)],
            agent_relations=[Creator(agent=Person(1, identifiers=[AgentIdentifier(14)]))]
        )], 'person', 'people', ['name']),
    ])
    def test_get_data(self, generator, model, route, controlled_values, client, Graph, ingest):
        ingest(Graph(initial))

        graph = Graph(*generator)
        Regulator().regulate(graph)
        instance_map = GraphDisambiguator().find_instances(graph)

        for node in graph:
            if node.type == model:
                expected = node
                expected_id = IDObfuscator.encode(instance_map[node])
                break
        response = client.get('/api/v2/{}/{}/'.format(route, expected_id))

        actual = json.loads(response.content.decode(encoding='UTF-8'))

        assert response.status_code == 200
        assert actual['data']['id'] == expected_id
        assert actual['data']['attributes']['type'] == expected.type
        for value in controlled_values:
            assert actual['data']['attributes'][value] == expected[camelCase_to_underscore(value)]

    def test_can_delete_work(self, client, normalized_data_id):
        preprint = factories.AbstractCreativeWorkFactory(is_deleted=False)
        preprint.administrative_change(type='share.dataset')
        assert preprint.is_deleted is False

        encoded_id = IDObfuscator.encode(preprint)
        response = client.get('/api/v2/datasets/{}/'.format(encoded_id))
        assert response.status_code == 200

        preprint.administrative_change(is_deleted=True)
        assert preprint.is_deleted is True

        response = client.get('/api/v2/datasets/{}/'.format(encoded_id))
        assert response.status_code == 403
        assert response.json() == {"errors": [{"source": {"pointer": "/data"}, "detail": "This data set has been removed.", "status": "403"}]}

        response = client.get('/api/v2/datasets/')
        assert response.status_code == 200
        assert response.json() == {'data': [], 'links': {'next': None, 'prev': None}}


@pytest.mark.django_db
@pytest.mark.parametrize('endpoint, factory', [
    ('agents', factories.AbstractAgentFactory),
    ('creativeworks', factories.AbstractCreativeWorkFactory),
    ('normalizeddata', factories.NormalizedDataFactory),
    ('rawdata', factories.RawDatumFactory),
])
class TestPagination:

    def test_no_prev(self, client, endpoint, factory):
        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        assert resp.json()['data'] == []
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_one(self, client, endpoint, factory):
        factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_full_page(self, client, endpoint, factory):
        for _ in range(10):
            factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200

        assert len(resp.json()['data']) == 10
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_next_page(self, client, endpoint, factory):
        for _ in range(20):
            factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200

        assert len(resp.json()['data']) == 10
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is not None
        assert 'page%5Bcursor%5D' in resp.json()['links']['next']

        resp2 = client.get(resp.json()['links']['next'])
        assert resp2.status_code == 200
        assert resp2.json()['links']['next'] is None

        assert set(x['id'] for x in resp.json()['data']) & set(x['id'] for x in resp2.json()['data']) == set()

    def test_bad_cursor(self, client, endpoint, factory):
        resp = client.get('/api/v2/creativeworks/', {'page[cursor]': 1})
        assert resp.status_code == 404
        assert resp.json() == {'errors': [{
            'status': '404',
            'detail': 'Invalid cursor',
            'source': {'pointer': '/data'},
        }]}
