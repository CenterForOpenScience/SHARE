import logging

from lxml import etree

from share.normalize import links
from share.normalize import parsers
from share.normalize.normalizer import Normalizer


# NOTE: Context is a thread local singleton
# It is asigned to ctx here just to keep a family interface
ctx = links.Context()
logger = logging.getLogger(__name__)


class OAIPerson(parsers.Parser):
    schema = 'Person'

    suffix = links.ParseName(ctx).suffix
    family_name = links.ParseName(ctx).last
    given_name = links.ParseName(ctx).first
    additional_name = links.ParseName(ctx).middle


class OAIContributor(parsers.Parser):
    schema = 'Contributor'

    person = links.Delegate(OAIPerson, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class OAIPublisher(parsers.Parser):
    schema = 'Publisher'
    name = ctx


class OAIAssociation(parsers.Parser):
    schema = 'Association'


class OAITag(parsers.Parser):
    schema = 'Tag'
    name = ctx


class OAIThroughTags(parsers.Parser):
    schema = 'ThroughTags'
    tag = links.Delegate(OAITag, ctx)


class OAICreativeWork(parsers.Parser):
    schema = 'CreativeWork'

    title = ctx.record.metadata['oai_dc:dc']['dc:title']
    rights = ctx.record.metadata['oai_dc:dc']['dc:rights']
    language = ctx.record.metadata['oai_dc:dc']['dc:language']
    description = links.Join(links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:description'))

    published = links.ParseDate(ctx.record.metadata['oai_dc:dc']['dc:date'][0])

    publishers = links.Map(
        links.Delegate(OAIAssociation.using(entity=links.Delegate(OAIPublisher))),
        links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:publisher')
    )

    rights = links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:rights')
    language = links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:language')

    # TODO: Contributors include a person, an organization, or a service
    # differentiate between them
    contributors = links.Map(
        links.Delegate(OAIContributor),
        links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:creator'),
        links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:contributor'),
    )

    tags = links.Map(
        links.Delegate(OAIThroughTags),
        links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:type'),
        links.Maybe(ctx.record.metadata['oai_dc:dc'], 'dc:subject')
    )

    # TODO Add links

    # TODO: need to determine which contributors/creators are institutions
    # institutions = ShareManyToManyField(Institution, through='ThroughInstitutions')

    # venues = ShareManyToManyField(Venue, through='ThroughVenues')
    # funders = ShareManyToManyField(Funder, through='ThroughFunders')
    # awards = ShareManyToManyField(Award, through='ThroughAwards')
    # data_providers = ShareManyToManyField(DataProvider, through='ThroughDataProviders')
    # provider_link = models.URLField(blank=True)

    # TODO: ask for clarification on difference between subject and tags
    # subject = ShareForeignKey(Tag, related_name='subjected_%(class)s', null=True)

    # TODO: parse all identifiers (there can be many identifiers) for 'doi:' and DOI_BASE_URL
    # doi = models.URLField(blank=True, null=True)

    # TODO: parse text of identifiers to find 'ISBN' also what is ISSN?
    # isbn = models.URLField(blank=True)

    # TODO:update model to handle this
    # work_type = ctx.record.metadata('oai_dc:dc')('dc:type')['*']

    # created = models.DateTimeField(null=True)
    # published = models.DateTimeField(null=True)
    # free_to_read_type = models.URLField(blank=True)
    # free_to_read_date = models.DateTimeField(null=True)

    # TODO: ask about format field
    # TODO: add publisher field


class OAIPreprint(OAICreativeWork):
    schema = 'Preprint'


class OAIPublication(OAICreativeWork):
    schema = 'Publication'


class OAINormalizer(Normalizer):

    @property
    def root_parser(self):
        return {
            'preprint': OAIPreprint,
            'publication': OAIPublication,
            'creativework': OAICreativeWork,
        }[self.config.emitted_type.lower()]

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
