from unittest import mock

import pytest

from share.tasks import schedule_reingest


@pytest.mark.django_db
def test_schedule_reingest(source_config):
    for yes_renormalize in (True, False):
        for yes_reformat in (True, False):
            with mock.patch('django.core.management.call_command') as mock_call_command:
                schedule_reingest.apply(
                    (source_config.pk,),
                    {
                        'pls_renormalize': yes_renormalize,
                        'pls_reformat': yes_reformat,
                    },
                )
                mock_call_command.assert_called_once_with(
                    'format_metadata_records',
                    source_config=[source_config.label],
                    pls_ensure_ingest_jobs=True,
                    pls_renormalize=yes_renormalize,
                    pls_reformat=yes_reformat,
                )
