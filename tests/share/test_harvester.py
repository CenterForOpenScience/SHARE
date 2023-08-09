from unittest import mock
import datetime
import pytest

import pendulum
import stevedore
import pkg_resources

from share.harvest.base import BaseHarvester
from share.harvest.serialization import DeprecatedDefaultSerializer, StringLikeSerializer
from share.util.extensions import Extensions

from tests import factories


@pytest.fixture(scope='class')
def mock_harvester_key():
    stevedore.ExtensionManager('share.harvesters')  # Force extensions to load
    _harvester_key = 'mockmock'

    class MockHarvester(BaseHarvester):
        KEY = _harvester_key
        VERSION = 1
        SERIALIZER_CLASS = StringLikeSerializer
        _do_fetch = factories.ListGenerator()

    mock_entry = mock.create_autospec(pkg_resources.EntryPoint, instance=True)
    mock_entry.name = _harvester_key
    mock_entry.module_name = _harvester_key
    mock_entry.resolve.return_value = MockHarvester
    stevedore.ExtensionManager.ENTRY_POINT_CACHE['share.harvesters'].append(mock_entry)
    Extensions._load_namespace('share.harvesters')
    return _harvester_key


@pytest.mark.usefixtures('nested_django_db')
class TestHarvesterInterface:

    @pytest.fixture(scope='class', params=[(True, True), (True, False), (False, True), (False, False)])
    def source_config(self, request, class_scoped_django_db, mock_harvester_key):
        config_disabled, source_deleted = request.param
        return factories.SourceConfigFactory(
            disabled=config_disabled,
            source__is_deleted=source_deleted,
            harvester_key=mock_harvester_key,
        )

    @pytest.fixture(scope='class')
    def harvester(self, source_config, class_scoped_django_db):
        return source_config.get_harvester()

    def test_passes_kwargs(self, source_config):
        config_kwargs = {
            'one': 'kwarg',
            'another': 'kwarg',
        }
        custom_kwargs = {
            'test': 'value',
            'one': 'overridden',
        }
        start = pendulum.parse('2017-07-01')
        end = pendulum.parse('2017-07-05')
        source_config.harvester_kwargs = config_kwargs
        harvester = source_config.get_harvester()
        harvester._do_fetch = mock.MagicMock()

        [x for x in harvester.fetch_date_range(start, end, **custom_kwargs)]

        harvester._do_fetch.assert_called_once_with(start, end, **{**config_kwargs, **custom_kwargs})

    def test_no_do_harvest(self, harvester):
        assert not hasattr(harvester, 'do_harvest')

    def test__do_fetch_not_implemented(self, harvester):
        with pytest.raises(NotImplementedError):
            BaseHarvester._do_fetch(harvester, None, None)

    def test_fetch_date(self, harvester, monkeypatch):
        monkeypatch.setattr(harvester, 'fetch_date_range', mock.Mock(), raising=False)

        harvester.fetch_date(pendulum.parse('2016-01-05'), custom='kwarg')

        assert harvester.fetch_date_range.assert_called_once_with(
            pendulum.parse('2016-01-04'),
            pendulum.parse('2016-01-05'),
            custom='kwarg'
        ) is None

    @pytest.mark.parametrize('start, end', [
        (1, 2),
        (0, None),
        (None, None),
        ('2016-01-01', '2015-01-01'),
        (pendulum.parse('2016-01-01').date(), datetime.timedelta(days=1)),
    ])
    def test_requires_dates(self, harvester, start, end):
        with pytest.raises(TypeError):
            list(harvester.fetch_date_range(start, end))

    def test_start_must_be_before_end(self, harvester):
        with pytest.raises(ValueError) as e:
            list(harvester.fetch_date_range(
                pendulum.parse('2016-01-05'),
                pendulum.parse('2016-01-04'),
            ))
        assert e.value.args == ("start must be before end. DateTime(2016, 1, 5, 0, 0, 0, tzinfo=Timezone('UTC')) > DateTime(2016, 1, 4, 0, 0, 0, tzinfo=Timezone('UTC'))", )

    def test__do_fetch_must_be_generator(self, harvester):
        harvester._do_fetch = lambda *_, **__: [1, 2]

        with pytest.raises(TypeError) as e:
            list(harvester.fetch())

        assert e.value.args == ('{!r}._do_fetch must return a GeneratorType for optimal performance and memory usage'.format(harvester), )

    def test_harvest_no_pretty(self, harvester):
        assert harvester.serializer.pretty is False
        harvester.serializer.pretty = True

        assert harvester.serializer.pretty is True
        with pytest.raises(ValueError) as e:
            list(harvester.harvest())

        assert e.value.args == ('To ensure that data is optimally deduplicated, harvests may not occur while using a pretty serializer.', )

    def fetch_pretty(self, harvester):
        assert harvester.serializer.pretty is False
        list(harvester.fetch())

        harvester.serializer.pretty = True

        assert harvester.serializer.pretty is True
        list(harvester.fetch())


@pytest.mark.usefixtures('nested_django_db')
class TestHarvesterBackwardsCompat:

    @pytest.fixture(scope='class')
    def source_config(self, class_scoped_django_db, mock_harvester_key):
        return factories.SourceConfigFactory(harvester_key=mock_harvester_key)

    @pytest.fixture(scope='class')
    def harvester(self, source_config, class_scoped_django_db):
        harvester = source_config.get_harvester()
        harvester.serializer = DeprecatedDefaultSerializer()
        return harvester

    def test_fetch_date_range_calls_do_harvest(self, harvester, monkeypatch):
        monkeypatch.setattr(harvester, 'do_harvest', mock.Mock(), raising=False)

        BaseHarvester._do_fetch(
            harvester,
            pendulum.parse('2017-01-01').date(),
            pendulum.parse('2017-01-02').date(),
        )

        assert harvester.do_harvest.assert_called_once_with(
            pendulum.parse('2017-01-01').date(),
            pendulum.parse('2017-01-02').date(),
        ) is None

    def test_default_serializer(self, harvester):
        assert isinstance(harvester.serializer.serialize('data'), str)
        assert isinstance(harvester.serializer.serialize(b'data'), str)
        assert isinstance(harvester.serializer.serialize({'data': 'value'}), str)

    def test_calls_shift_range(self, harvester, monkeypatch):
        monkeypatch.setattr(harvester, 'shift_range', mock.Mock(return_value=(1, 2)), raising=False)
        list(harvester.fetch())
        assert harvester.shift_range.called is True
