import pytest

from tests.factories import (
    RawDatumFactory,
    SourceUniqueIdentifierFactory,
)


@pytest.mark.django_db
class TestSourceUniqueIdentifier:

    def test_most_recent_raw_datum(self):
        suid = SourceUniqueIdentifierFactory()

        RawDatumFactory(suid=suid, datestamp=None, date_created='2021-01-01 00:00Z')
        expected = RawDatumFactory(suid=suid, datestamp='2021-01-04 00:00Z')
        RawDatumFactory(suid=suid, datestamp='2021-01-01 00:00Z')
        RawDatumFactory(suid=suid, datestamp='2021-01-02 00:00Z')
        RawDatumFactory(suid=suid, datestamp='2021-01-03 00:00Z')

        actual = suid.most_recent_raw_datum()
        assert expected == actual

    def test_most_recent_raw_datum__datestamp_wins(self):
        suid = SourceUniqueIdentifierFactory()

        RawDatumFactory(suid=suid, datestamp='2021-01-01 00:00Z', date_created='2021-01-02 00:00Z')
        expected = RawDatumFactory(suid=suid, datestamp='2021-01-02 00:00Z', date_created='2021-01-01 00:00Z')

        actual = suid.most_recent_raw_datum()
        assert expected == actual

    def test_most_recent_raw_datum_no_datestamps(self):
        suid = SourceUniqueIdentifierFactory()

        expected = RawDatumFactory(suid=suid, datestamp=None, date_created='2021-01-02 00:00Z')
        RawDatumFactory(suid=suid, datestamp=None, date_created='2021-01-01 00:00Z')

        actual = suid.most_recent_raw_datum()
        assert expected == actual

    def test_date_first_seen(self):
        suid = SourceUniqueIdentifierFactory()

        expected = RawDatumFactory(suid=suid).date_created
        for _ in range(7):
            RawDatumFactory(suid=suid)

        actual = suid.get_date_first_seen()
        assert expected == actual

    def test_date_first_seen_when_no_data(self):
        suid = SourceUniqueIdentifierFactory()
        actual = suid.get_date_first_seen()
        assert actual is None
