from unittest import mock
import datetime
import pytest

import pendulum

from share.harvest.base import BaseHarvester
from share.harvest.exceptions import HarvesterDisabledError

from tests import factories


@pytest.mark.django_db
class TestHarvesterInterface:

    @pytest.fixture(autouse=True)
    def source_config(self):
        return factories.SourceConfigFactory()

    @pytest.fixture
    def harvester(self, source_config):
        return source_config.get_harvester()

    def test_passes_kwargs(self, harvester):
        harvester._do_fetch = mock.Mock(return_value=[])

        list(harvester.fetch_date_range(
            pendulum.parse('2017-01-01').date(),
            pendulum.parse('2017-01-02').date(),
            limit=10,
            test='value'
        ))

        assert harvester._do_fetch.assert_called_once_with(
            pendulum.parse('2017-01-01').in_timezone('UTC'),
            pendulum.parse('2017-01-02').in_timezone('UTC'),
            test='value'
        ) is None

    def test_no_do_harvest(self, harvester):
        assert not hasattr(harvester, 'do_harvest')

    def test__do_fetch_not_implemented(self, harvester):
        with pytest.raises(NotImplementedError):
            BaseHarvester._do_fetch(harvester, None, None)

    def test_fetch_id_not_implemented(self, harvester):
        with pytest.raises(NotImplementedError):
            harvester.fetch_id('myid')

    def test_fetch_date(self, harvester):
        harvester.fetch_date_range = mock.Mock()

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
        assert e.value.args == ('start must be before end. <Pendulum [2016-01-05T00:00:00+00:00]> > <Pendulum [2016-01-04T00:00:00+00:00]>', )

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


@pytest.mark.django_db
class TestHarvesterBackwardsCompat:

    @pytest.fixture(autouse=True)
    def source_config(self):
        return factories.SourceConfigFactory()

    @pytest.fixture
    def harvester(self, source_config):
        return source_config.get_harvester()

    def test_fetch_date_range_calls_do_harvest(self, harvester):
        harvester.do_harvest = mock.Mock()

        BaseHarvester._do_fetch(
            harvester,
            pendulum.parse('2017-01-01').date(),
            pendulum.parse('2017-01-02').date(),
            limit=10,
            test='value'
        )

        assert harvester.do_harvest.assert_called_once_with(
            pendulum.parse('2017-01-01').date(),
            pendulum.parse('2017-01-02').date(),
            limit=10,
            test='value'
        ) is None

    def test_default_serializer(self, harvester):
        assert isinstance(harvester.serializer.serialize('data'), str)
        assert isinstance(harvester.serializer.serialize(b'data'), str)
        assert isinstance(harvester.serializer.serialize({'data': 'value'}), str)

    def test_calls_shift_range(self, harvester):
        harvester.shift_range = mock.Mock(return_value=(1, 2))
        list(harvester.fetch())
        assert harvester.shift_range.called is True


@pytest.mark.django_db
class TestHarvesterDisabledSourceConfig:

    def test_disabled_source_config(self):
        sc = factories.SourceConfigFactory(disabled=True)
        with pytest.raises(HarvesterDisabledError):
            list(sc.get_harvester().harvest())

    def test_deleted_source(self):
        sc = factories.SourceConfigFactory(source__is_deleted=True)
        with pytest.raises(HarvesterDisabledError):
            list(sc.get_harvester().harvest())

    def test_ignores_disabled(self):
        sc = factories.SourceConfigFactory(disabled=True)
        assert list(sc.get_harvester().harvest(ignore_disabled=True)) == []

    def test_ignores_deleted(self):
        sc = factories.SourceConfigFactory(source__is_deleted=True)
        assert list(sc.get_harvester().harvest(ignore_disabled=True)) == []
