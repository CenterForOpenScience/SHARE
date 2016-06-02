import os
import json
import feedparser

from django.utils import timezone


class Harvester():

    VERSION = 1

    def all(self):
        url = 'http://export.arxiv.org/api/query?search_query=all' +\
            '&start=0' +\
            '&sortBy=lastUpdatedDate' +\
            '&sortOrder=descending' +\
            '&max_results=10'
        return feedparser.parse(url).entries

    def by_date(self, start, finish):
        pass

class NormalizerNew(ShareNormalized):
    def __init__(self):
        Manuscript(
            title=self.json['title'].trim()).save()
        for contributor in self.json['arxiv_authors']:
            Contributor(

            ).save()


class NoramlizerUpdates():
    pass

class NormalizerDeletes():
    pass


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'share.settings')
    import django
    django.setup()
    result = Harvester().all()
    from raw.models import Raw
    Raw(
        harvester='org.arxiv.api',
        date_harvested=timezone.now(),
        data=result
    ).save()