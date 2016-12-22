import logging

import datetime
import requests
from django.core.urlresolvers import reverse

from project import settings
from share.models import NormalizedData

from share.tasks import AppTask

logger = logging.getLogger(__name__)


class CurateItemTask(AppTask):

    def do_run(self, matches):
        # use the oldest record from the order by specified
        into_id = matches.pop()
        json_ld = {
            '@id': '_:{}'.format(into_id),
            '@type': 'MergeAction',
            'into': {'@type': 'Tag', '@id': into_id},
            'from': []
        }
        for from_id in matches:
            json_ld['from'].append({'@type': 'Tag', '@id': from_id})
        graph = {'@graph': [json_ld]}

        try:
            normalized_data_url = settings.SHARE_API_URL[0:-1] + reverse('api:normalizeddata-list')
            resp = requests.post(normalized_data_url, json={
                'created_at': datetime.datetime.utcnow().isoformat(),
                'data': graph,
            }, headers={'Authorization': self.config.authorization()})
        except Exception as e:
            logger.exception('Failed task (%s, %d)', self.config.label, into_id)
            raise self.retry(countdown=10, exc=e)

        # attach task
        normalized_id = resp.json()['normalized_id']
        normalized = NormalizedData.objects.get(pk=normalized_id)
        normalized.tasks.add(self.task)
        normalized.save()

        logger.info('Created changeset for tag %d found %d matche(s)', into_id, len(matches))
