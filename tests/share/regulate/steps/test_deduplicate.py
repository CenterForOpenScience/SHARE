import pytest

from share.regulate.steps.deduplicate import Deduplicate

from tests.share.normalize.factories import *


class TestDeduplicate:
    @pytest.mark.parametrize('input', [
        [Preprint(0, identifiers=[WorkIdentifier(1)])]
    ])
    def test_no_change(self, Graph, input):
        graph = Graph(input)
        Deduplicate().run(graph)
        assert graph == Graph(input)

    @pytest.mark.parametrize('input, output', [
        ([
            Preprint(0, identifiers=[WorkIdentifier(id=1, uri='http://osf.io/guidguid')]),
            CreativeWork(id=1, sparse=True, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')]),
        ]),
        ([
            Preprint(0, identifiers=[
                WorkIdentifier(uri='http://osf.io/guidguid'),
                WorkIdentifier(4),
            ]),
            CreativeWork(id=1, sparse=True, identifiers=[WorkIdentifier(uri='http://osf.io/guidguid')])
        ], [
            Preprint(0, identifiers=[
                WorkIdentifier(4),
                WorkIdentifier(uri='http://osf.io/guidguid'),
            ]),
        ])
    ])
    def test_deduplicate(self, Graph, input, output):
        graph = Graph(input)
        Deduplicate().run(graph)
        assert graph == Graph(output)
