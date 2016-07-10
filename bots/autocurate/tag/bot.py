import logging

from share.bot import Bot
from share.models import Tag

from .tasks import CurateItemTask


logger = logging.getLogger(__name__)


class AutoCurateBot(Bot):

    def run(self, dry=False):
        submitted = set()

        qs = Tag.objects.filter(
            date_modified__gte=self.last_run.datetime,
        )

        total = qs.count()
        logger.info('Found %s tags eligible for automatic curation', total)

        for row in qs:
            if row.id in submitted:
                continue

            matches = list(
                Tag.objects.filter(
                    name__iexact=row.name,
                ).order_by('-date_modified').values_list('id', flat=True)
            )

            if len(matches) > 1:
                submitted = submitted.union(set(matches))
                CurateItemTask().apply_async((self.config.label, self.started_by, matches,))
