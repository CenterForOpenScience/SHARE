import datetime
import time

from django.db.models import OuterRef

from trove.util.django import pk_chunked

from share import models as share_db
from share.management.commands import BaseShareCommand
from trove import models as trove_db


class Command(BaseShareCommand):
    # copy all non-null values from `RawDatum.expiration_date` to `SupplementaryIndexcardRdf.expiration_date`
    # (while being overly cautious to avoid joins on `RawDatum` or `SourceUniqueIdentifier`)
    # meant to be run after trove migration 0008_expiration_dates, before share.RawDatum is deleted

    def add_arguments(self, parser):
        parser.add_argument('--chunk-size', type=int, default=666)
        parser.add_argument('--today', type=datetime.date.fromisoformat, default=datetime.date.today())
        parser.add_argument('--continue-after', type=str, default=None)

    def handle(self, *args, chunk_size: int, today: datetime.date, continue_after, **kwargs):
        _before = time.perf_counter()
        _total_updated = 0
        _raw_qs = (
            share_db.RawDatum.objects.latest_for_each_suid()
            .filter(expiration_date__gt=today)  # ignore the expired (and the non-expiring)
        )
        if continue_after is not None:
            _raw_qs = _raw_qs.filter(pk__gt=continue_after)
        for _raw_pk_chunk in pk_chunked(_raw_qs, chunk_size):
            _supp_qs = trove_db.SupplementaryIndexcardRdf.objects.filter(
                from_raw_datum_id__in=_raw_pk_chunk,
                expiration_date__isnull=True,  # avoid overwriting non-null values
            )
            _updated_count = _supp_qs.update(
                expiration_date=share_db.RawDatum.objects.filter(
                    id=OuterRef('from_raw_datum_id'),
                ).values('expiration_date'),
            )
            _total_updated += _updated_count
            _last_pk = _raw_pk_chunk[-1]
            _elapsed = time.perf_counter() - _before
            self.stdout.write(
                f'{_elapsed:.2f}: migrated {_updated_count} of {len(_raw_pk_chunk)}  --continue-after={_last_pk}',
            )
        _total_seconds = time.perf_counter() - _before
        self.stdout.write(
            self.style.SUCCESS(f'done! migrated {_total_updated} in {_total_seconds}s'),
        )
