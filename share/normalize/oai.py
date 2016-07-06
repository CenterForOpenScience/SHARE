import logging

from lxml import etree

from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer
from share.normalize.utils import format_doi_as_url


logger = logging.getLogger(__name__)


class OAILink(Parser):
    schema = 'Link'

    url = tools.RunPython('format_link', ctx)
    type = tools.RunPython('get_link_type', ctx)

    # TODO: account for other types of links
    # i.e. ISBN

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        # TODO: id there a way to get current provider name?
        # if 'figshare.com' in link:
        #     return 'provider'
        return 'misc'

    def format_link(self, link):
        link_type = self.get_link_type(link)
        if link_type == 'doi':
            return format_doi_as_url(self, link)
        return link


class OAIThroughLinks(Parser):
    schema = 'ThroughLinks'

    link = tools.Delegate(OAILink, ctx)


class OAIPerson(Parser):
    schema = 'Person'

    suffix = tools.ParseName(ctx).suffix
    family_name = tools.ParseName(ctx).last
    given_name = tools.ParseName(ctx).first
    additional_name = tools.ParseName(ctx).middle


class OAIContributor(Parser):
    schema = 'Contributor'

    person = tools.Delegate(OAIPerson, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class OAIPublisher(Parser):
    schema = 'Publisher'
    name = ctx


class OAIAssociation(Parser):
    schema = 'Association'


class OAITag(Parser):
    schema = 'Tag'
    name = ctx


class OAIThroughTags(Parser):
    schema = 'ThroughTags'
    tag = tools.Delegate(OAITag, ctx)


class OAICreativeWork(Parser):
    schema = 'CreativeWork'

    title = tools.Join(ctx.record.metadata['oai_dc:dc']['dc:title'])
    description = tools.Join(tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:description'))

    publishers = tools.Map(
        tools.Delegate(OAIAssociation.using(entity=tools.Delegate(OAIPublisher))),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:publisher')
    )

    rights = tools.Join(tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:rights'))

    language = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:language')

    # TODO: Contributors include a person, an organization, or a service
    # differentiate between them
    contributors = tools.Map(
        tools.Delegate(OAIContributor),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:creator'),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:contributor'),
    )

    tags = tools.Map(
        tools.Delegate(OAIThroughTags),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:type'),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:subject'),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:format'),
        tools.Maybe(ctx.record.header, 'setSpec')
    )

    links = tools.Map(
        tools.Delegate(OAIThroughLinks),
        tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:identifier')
    )

    date_updated = tools.ParseDate(ctx.record.header.datestamp)

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        # An entity responsible for making contributions to the resource.
        contributor = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:contributor')

        # The spatial or temporal topic of the resource, the spatial applicability of the resource,
        # or the jurisdiction under which the resource is relevant.
        coverage = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:coverage')

        # An entity primarily responsible for making the resource.
        creator = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:creator')

        # A point or period of time associated with an event in the lifecycle of the resource.
        dates = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:date')

        # The file format, physical medium, or dimensions of the resource.
        resource_format = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:format')

        # An unambiguous reference to the resource within a given context.
        identifiers = tools.Concat(
            ctx.record.metadata['oai_dc:dc']['dc:identifier'],
            tools.Maybe(ctx.record.header, 'identifier')
        )

        # A related resource.
        relation = tools.RunPython('get_relation', ctx)

        # A related resource from which the described resource is derived.
        source = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:source')

        # The topic of the resource.
        subject = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:subject')

        # The nature or genre of the resource.
        resource_type = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:type')

        set_spec = tools.Maybe(ctx.record.header, 'setSpec')

    def get_relation(self, ctx):
        base = ctx['record']['metadata']['oai_dc:dc']
        try:
            base['dc:relation']
        except KeyError:
            return []
        else:
            try:
                base['dc:relation']['#text']
            except TypeError:
                return base['dc:relation']


class OAIPreprint(OAICreativeWork):
    schema = 'Preprint'


class OAIPublication(OAICreativeWork):
    schema = 'Publication'


class OAINormalizer(Normalizer):

    @property
    def root_parser(self):
        parser = {
            'preprint': OAIPreprint,
            'publication': OAIPublication,
            'creativework': OAICreativeWork,
        }[self.config.emitted_type.lower()]

        if self.config.property_list:
            logger.debug('Attaching addition properties %s to normalizer for %s'.format(self.config.property_list, self.config.label))
            for prop in self.config.property_list:
                parser._extra[prop] = tools.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:' + prop).chain()[0]

        return parser

    def do_normalize(self, data):
        if self.config.approved_sets is not None:
            specs = set(x.replace('publication:', '') for x in etree.fromstring(data).xpath(
                'ns0:header/ns0:setSpec/node()',
                namespaces={'ns0': 'http://www.openarchives.org/OAI/2.0/'}
            ))
            if not (specs & set(self.config.approved_sets)):
                logger.warning('Series %s not found in approved_sets for %s', specs, self.config.label)
                return None

        return super().do_normalize(data)
