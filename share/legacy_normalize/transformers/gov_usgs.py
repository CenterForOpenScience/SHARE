import re
from share.legacy_normalize.transform.chain import *

EMAIL_RE = re.compile(r'\S+@\S+')


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class AgentIdentifier(Parser):
    uri = IRI(ctx, urn_fallback=True)


class RelatedAgent(Parser):
    schema = GuessAgentType(ctx, default='organization')

    name = ctx


class IsAffiliatedWith(Parser):
    related = Delegate(RelatedAgent, ctx)


class AbstractAgent(Parser):
    identifiers = Map(
        Delegate(AgentIdentifier),
        Try(ctx.email),
        RunPython('to_str', ctx.contributorId)
    )

    related_agents = Map(
        Delegate(IsAffiliatedWith),
        Try(ctx.affiliation.text),
        RunPython('maybe_usgs', Try(ctx.usgs))
    )

    def to_str(self, obj):
        return str(obj)

    def maybe_usgs(self, obj):
        if obj:
            # How USGS references itself as a work publisher
            return 'U.S. Geological Survey'
        return None


class Organization(AbstractAgent):
    schema = GuessAgentType(ctx.text, default='organization')

    name = ctx.text


class Person(AbstractAgent):
    given_name = Maybe(ctx, 'given')
    family_name = Maybe(ctx, 'family')


class Creator(Parser):
    order_cited = ctx('index')
    cited_as = RunPython('strip_emails', ctx.text)
    agent = Delegate(Person, ctx)

    def strip_emails(self, obj):
        return EMAIL_RE.sub('', obj)


class PublisherAgent(Parser):
    schema = GuessAgentType(ctx.publisher, default='organization')

    name = ctx.publisher
    location = Try(ctx.publisherLocation)


class Publisher(Parser):
    agent = Delegate(PublisherAgent, ctx)


class CreativeWork(Parser):
    schema = RunPython('get_schema', ctx.publicationType.text)

    title = ctx.title
    description = Maybe(ctx, 'docAbstract')
    date_updated = ParseDate(ctx.lastModifiedDate)
    date_published = ParseDate(ctx.displayToPublicDate)
    language = Maybe(ctx, 'language')

    related_agents = Concat(
        Map(
            Delegate(Creator),
            Filter(lambda a: not a['corporation'], Try(ctx.contributors.authors))
        ),
        Map(
            Delegate(Creator.using(agent=Delegate(Organization, ctx))),
            Filter(lambda a: a['corporation'], Try(ctx.contributors.authors))
        ),
        Try(Delegate(Publisher, ctx))
    )

    identifiers = Map(
        Delegate(WorkIdentifier),
        RunPython('format_usgs_id_as_url', ctx.indexId),
        Try(ctx.doi)
    )

    class Extra:
        additional_online_files = Maybe(ctx, 'additionalOnlineFiles')
        country = Maybe(ctx, 'country')
        defined_type = Maybe(ctx, 'defined_type')
        end_page = Maybe(ctx, 'endPage')
        geographic_extents = Maybe(ctx, 'geographicExtents')
        index_id = Maybe(ctx, 'indexId')
        ipds_id = Maybe(ctx, 'ipdsId')
        issue = Maybe(ctx, 'issue')
        links = Maybe(ctx, 'links')
        online_only = Maybe(ctx, 'onlineOnly')
        other_geospatial = Maybe(ctx, 'otherGeospatial')
        publication_subtype = Maybe(ctx, 'publicationSubtype')
        publication_year = Maybe(ctx, 'publicationYear')
        start_page = Maybe(ctx, 'startPage')
        state = Maybe(ctx, 'state')
        type = Maybe(ctx, 'type')
        volume = Maybe(ctx, 'volume')

    def get_schema(self, publication_type):
        return {
            'Article': 'Article',
            'Book': 'Book',
            'Book chapter': 'Book',
            'Conference Paper': 'ConferencePaper',
            'Dataset': 'DataSet',
            # 'Pamphlet':
            # 'Patent':
            'Report': 'Report',
            'Speech': 'Presentation',
            'Thesis': 'Thesis',
            # 'Videorecording':
        }.get(publication_type) or 'CreativeWork'

    def format_usgs_id_as_url(self, id):
        return 'https://pubs.er.usgs.gov/publication/{}'.format(id)


class USGSTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
