import logging

import arrow

from bots.autocurateperson.tasks import CurateItemTask
from share.bot import Bot
from share.models import CeleryProviderTask

from share.models import Person

logger = logging.getLogger(__name__)


class AutoCurateBot(Bot):

    def run(self, last_run, dry=False):
        if not last_run:
            logger.debug('Finding last successful job')
            last_run = CeleryProviderTask.objects.filter(
                app_label=self.config.label,
                status=CeleryProviderTask.STATUS.succeeded,
            ).order_by(
                '-timestamp'
            ).values_list('timestamp', flat=True).first()
            if last_run:
                last_run = arrow.get(last_run)
            else:
                last_run = arrow.get(0)
            logger.info('Found last job %s', last_run)
        else:
            last_run = arrow.get(last_run)

        logger.info('Using last run of %s', last_run)
        self.do_curation(last_run)

    def do_curation(self, last_run: arrow.Arrow):
        submitted = set()

        qs = Person.objects.filter(
            date_modified__gte=last_run.datetime,
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
