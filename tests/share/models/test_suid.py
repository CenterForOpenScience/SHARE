import pytest

from tests.factories import (
    IngestJobFactory,
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

    def test_ingest_job(self):
        suid = SourceUniqueIdentifierFactory()

        IngestJobFactory(suid=suid, date_started=None, date_created='2021-01-01 00:00Z')
        expected = IngestJobFactory(suid=suid, date_started='2021-01-02 00:00Z', date_created='2021-01-01 00:00Z')
        IngestJobFactory(suid=suid, date_started='2021-01-01 00:00Z', date_created='2021-01-01 00:00Z')

        actual = suid.ingest_job
        assert expected == actual

    def test_ingest_job__date_started_wins(self):
        suid = SourceUniqueIdentifierFactory()

        expected = IngestJobFactory(suid=suid, date_started='2021-01-02 00:00Z', date_created='2021-01-01 00:00Z')
        IngestJobFactory(suid=suid, date_started='2021-01-01 00:00Z', date_created='2021-01-03 00:00Z')

        actual = suid.ingest_job
        assert expected == actual
