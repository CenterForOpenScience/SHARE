import pytest

from tests.factories import SourceUniqueIdentifierFactory
from tests.trove.factories import create_indexcard, update_indexcard_content


@pytest.mark.django_db
class TestSourceUniqueIdentifier:

    def test_date_first_seen(self):
        indexcard = create_indexcard()
        suid = indexcard.source_record_suid
        expected = indexcard.archived_description_set.get().created
        for _ in range(7):
            update_indexcard_content(indexcard)

        actual = suid.get_date_first_seen()
        assert expected == actual

    def test_date_first_seen_when_no_data(self):
        suid = SourceUniqueIdentifierFactory()
        actual = suid.get_date_first_seen()
        assert actual is None
