import logging

from share.bot import Bot
from share.models import Change
from share.models import ChangeSet

logger = logging.getLogger(__name__)


class AutoMergeBot(Bot):

    def run(self, dry=False):
        qs = ChangeSet.objects.filter(
            status=ChangeSet.STATUS.pending,
            changes__type=Change.TYPE.create,
        ).exclude(
            submitted_by__robot=''
        ).distinct()

        logger.info('Found {} change sets eligible for automatic acceptance'.format(qs.count()))

        for cs in qs.all():
            cs.accept()
            logger.debug('Accepted change set {}'.format(cs))
