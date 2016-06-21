from lxml import etree

from share.normalize import *  # noqa


class Manuscript(AbstractManuscript):
    title = ctx.metadata[0].dc[0].title[0].text()
    contributors = ctx.metadata[0].dc[0].creator['*']
    description = Concat(ctx.metadata[0].dc[0].description['*'].text())


class Contributor(AbstractContributor):
    person = ctx


class Person(AbstractPerson):
    given_name = ParseName(ctx.text()).first
    family_name = ParseName(ctx.text()).last


class ArxivNormalizer(Normalizer):

    def do_normalize(self, raw_data):
        Manuscript(etree.fromstring(raw_data.data.decode())).parse()
        return ctx.graph
