import pytest

from share.util.osf import guess_osf_guid, get_guid_from_uri

from tests.share.normalize import factories as f


@pytest.mark.parametrize('uri, expected', [
    ('http://osf.io/mst3k/', 'mst3k'),
    ('https://osf.io/mst3k', 'mst3k'),
    ('http://staging.osf.io/mst3k', 'mst3k'),
    ('https://staging.osf.io/mst3k/', 'mst3k'),
    ('http://staging2.osf.io/mst3k', 'mst3k'),
    ('https://test.osf.io/mst3k', 'mst3k'),
    ('https://future-staging.osf.io/mst3k/', 'mst3k'),
    ('http://osf.io/mst3k/files', None),
    ('https://nope.staging.osf.io/mst3k', None),
    ('https://example.com', None),
    ('foo', None),
    ('https://meow.osfdio/mst3k', None),
    ('https://osflio/mst3k', None),
    ('https://meowosf.io/mst3k', None),
])
def test_get_guid_from_uri(uri, expected):
    actual = get_guid_from_uri(uri)
    assert actual == expected


@pytest.mark.parametrize('graph_input, expected', [
    (f.CreativeWork(), None),
    (f.CreativeWork(
        identifiers=[f.WorkIdentifier(uri='http://osf.io/mst3k')],
    ), 'mst3k'),
    (f.CreativeWork(
        identifiers=[
            f.WorkIdentifier(uri='http://osf.io/mst3k'),
            f.WorkIdentifier(uri='http://osf.io/ohnoe'),
        ],
    ), None),
    ([
        f.CreativeWork(
            sparse=True,
            id='a',
            identifiers=[f.WorkIdentifier(uri='http://osf.io/mst3k')],
        ),
        f.CreativeWork(
            sparse=True,
            id='b',
            title='this one',
            identifiers=[f.WorkIdentifier(uri='http://osf.io/other')],
        ),
    ], 'other'),
    (f.Agent(), None),
])
def test_guess_osf_guid(Graph, graph_input, expected):
    actual = guess_osf_guid(Graph(graph_input))
    assert actual == expected
