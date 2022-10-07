import pytest

from share.legacy_normalize.regulate.steps.deduplicate import Deduplicate

from tests.share.normalize.factories import (
    CreativeWork,
    Preprint,
    Registration,
    Subject,
    WorkIdentifier,
)


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
        ]),
        ([
            Registration(0, subjects=[
                Subject(
                    0,
                    name='custom-child',
                    central_synonym=Subject(1, name='central-child', parent=Subject(3, name='central-parent')),
                    parent=Subject(2, name='custom-parent', central_synonym=Subject(3, name='central-parent')),
                )
                for _ in range(3)
            ]),
        ], [
            Registration(0, subjects=[
                Subject(
                    0,
                    name='custom-child',
                    central_synonym=Subject(1, name='central-child', parent=Subject(3, id='central-parent', name='central-parent')),
                    parent=Subject(2, name='custom-parent', central_synonym=Subject(id='central-parent')),
                )
            ]),
        ]),
    ])
    def test_deduplicate(self, Graph, input, output):
        graph = Graph(input)
        Deduplicate().run(graph)
        assert graph == Graph(output)
