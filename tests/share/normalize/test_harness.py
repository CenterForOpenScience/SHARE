# flake8: noqa
import functools
from share import models


def _params(id=None, type=None, **kwargs):
    ret = {'id': id, 'type': type, **kwargs}
    if id is None:
        ret.pop('id')
    return ret

for model in dir(models):
    if not hasattr(getattr(models, model), 'VersionModel'):
        continue
    locals()[model] = functools.partial(_params, type=model.lower())


class TestShortHand:

    def test_id(self):
        assert Agent(0) == {'id': 0, 'type': 'agent'}
        assert Person(0) == {'id': 0, 'type': 'person'}
        assert Organization(0) == {'id': 0, 'type': 'organization'}
        assert Institution(0) == {'id': 0, 'type': 'institution'}

    def test_anon(self):
        assert CreativeWork() == {'type': 'creativework'}
        assert Article() == {'type': 'article'}
        assert Publication() == {'type': 'publication'}
        assert Patent() == {'type': 'patent'}

    def test_kwargs(self):
        kwargs = {'hello': 'World'}
        assert CreativeWork(**kwargs) == {'type': 'creativework', **kwargs}
        assert Article(**kwargs) == {'type': 'article', **kwargs}
        assert Publication(**kwargs) == {'type': 'publication', **kwargs}
        assert Patent(**kwargs) == {'type': 'patent', **kwargs}

    def test_nesting(self):
        assert CreativeWork(
            identifiers=[WorkIdentifier(0), WorkIdentifier(1)],
            related_works=[Preprint(identifiers=[WorkIdentifier(0)])]
        ) == {
            'type': 'creativework',
            'identifiers': [{'id': 0, 'type': 'workidentifier'}, {'id': 1, 'type': 'workidentifier'}],
            'related_works': [{
                'type': 'preprint',
                'identifiers': [{'id': 0, 'type': 'workidentifier'}]
            }]
        }
