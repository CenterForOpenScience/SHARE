import json

from share.core import Normalizer
from share.parsers import *  # noqa


class Person(AbstractPerson):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class Contributor(AbstractContributor):
    person = ctx


class Manuscript(AbstractManuscript):
    title = ctx.title
    description = ctx.description
    # publish_date = ParseDate(ctx.published_date)
    contributors = ctx.authors['*']


class FigshareNormalizer(Normalizer):

    def do_normalize(self, raw_data):
        Manuscript(json.loads(raw_data.data.decode())).parse()
        return ctx.graph
