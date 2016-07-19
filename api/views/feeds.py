from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.core import serializers

import requests

from share.models.creative import AbstractCreativeWork


SHARE_URL = 'https://staging-share.osf.io/api/search/abstractcreativework/_search'

class CreativeWorksRSS(Feed):
    title = "SHARE RSS Feed"
    link = "/rss/"
    description = "Updates to the SHARE dataset"

    def items(self):
        # TODO - make this filterable and probably not use only AbstractCreativeWorks
        # TODO - make use elasticsearch results?
        return AbstractCreativeWork.objects.order_by('-date_updated')[:5]

    def item_link(self, item):
        links = item.links.all()
        if links:
            return links[0].url
        else:
            return None

    def item_author_name(self, item):
        for contributor in item.contributors.all():
            return contributor.get_full_name()


class CreativeWorksAtom(CreativeWorksRSS):
    feed_type = Atom1Feed
    subtitle = CreativeWorksRSS.description