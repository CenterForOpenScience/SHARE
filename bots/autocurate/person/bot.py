import logging

from bots.autocurate.person.tasks import CurateItemTask
from share.bot import Bot

from share.models import Person

logger = logging.getLogger(__name__)


class AutoCurateBot(Bot):

    def run(self):
        submitted = set()

        qs = Person.objects.filter(
            date_modified__gte=self.last_run.datetime,
        )

        total = qs.count()
        logger.info('Found %s persons eligible for automatic curation', total)

        for row in qs:
            if row.id in submitted:
                continue

            matches = list(
                Person.objects.filter(
                    family_name=row.family_name,
                    given_name=row.given_name,
                    additional_name=row.additional_name,
                    suffix=row.suffix,
                ).order_by('-date_modified').values_list('id', flat=True)
            )

            if len(matches) > 1:
                submitted = submitted.union(set(matches))
                CurateItemTask().apply_async((self.config.label, self.started_by.id, matches,))
