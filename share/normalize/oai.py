import re
import logging
from lxml import etree

from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer


logger = logging.getLogger(__name__)


class OAIAgent(Parser):
    schema = tools.GuessAgentType(ctx)

    name = ctx


class OAIAgentIdentifier(Parser):
    schema = 'AgentIdentifier'

    uri = tools.IRI(ctx)


class OAIWorkIdentifier(Parser):
    schema = 'WorkIdentifier'

    uri = ctx


class OAISubject(Parser):
    schema = 'Subject'

    name = ctx


class OAIThroughSubjects(Parser):
    schema = 'ThroughSubjects'

    subject = tools.Delegate(OAISubject, ctx)


class OAITag(Parser):
    schema = 'Tag'

    name = ctx


class OAIThroughTags(Parser):
    schema = 'ThroughTags'

    tag = tools.Delegate(OAITag, ctx)


class OAIRelatedWork(Parser):
    schema = 'CreativeWork'

    identifiers = tools.Map(tools.Delegate(OAIWorkIdentifier), tools.IRI(ctx))

    class Extra:
        identifier = ctx


class OAIWorkRelation(Parser):
    schema = 'WorkRelation'

    related = tools.Delegate(OAIRelatedWork, ctx)


class OAIAgentWorkRelation(Parser):
    schema = 'AgentWorkRelation'

    agent = tools.Delegate(OAIAgent, ctx)
    cited_as = ctx


class OAIContributor(OAIAgentWorkRelation):
    schema = 'Contributor'


class OAICreator(OAIContributor):
    schema = 'Creator'

    order_cited = ctx('index')


class OAIPublisher(Parser):
    schema = 'Publisher'

    agent = tools.Delegate(OAIAgent.using(schema=tools.GuessAgentType(default='organization')), ctx)


class OAICreativeWork(Parser):
    default_type = None
    type_map = None

    schema = tools.RunPython(
        'get_schema',
        tools.OneOf(
            ctx.record.metadata.dc['dc:type'],
            tools.Static(None)
        )
    )

    title = tools.Join(tools.RunPython('force_text', tools.Try(ctx['record']['metadata']['dc']['dc:title'])))
    description = tools.Join(tools.RunPython('force_text', tools.Try(ctx.record.metadata.dc['dc:description'])))

    identifiers = tools.Map(
        tools.Delegate(OAIWorkIdentifier),
        tools.Map(
            tools.IRI(),
            tools.Try(ctx['record']['metadata']['dc']['dc:identifier']),
            tools.Try(ctx['record']['header']['identifier'])
        )
    )

    related_works = tools.Concat(
        tools.Map(
            tools.Delegate(OAIWorkRelation),
            tools.Map(
                tools.IRI(),
                tools.RunPython('get_relation', ctx)
            )
        )
    )

    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(OAICreator),
            tools.Try(ctx['record']['metadata']['dc']['dc:creator'])
        ),
        tools.Map(
            tools.Delegate(OAIContributor),
            tools.Try(ctx['record']['metadata']['dc']['dc:contributor'])
        ),
        tools.Map(
            tools.Delegate(OAIPublisher),
            tools.RunPython('force_text', tools.Try(ctx.record.metadata.dc['dc:publisher']))
        ),
    )

    rights = tools.Join(tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:rights'))

    # Note: this is only taking the first language in the case of multiple languages
    language = tools.ParseLanguage(
        tools.Try(ctx['record']['metadata']['dc']['dc:language'][0]),
    )

    subjects = tools.Map(
        tools.Delegate(OAIThroughSubjects),
        tools.Subjects(
            tools.Map(
                tools.RunPython('tokenize'),
                tools.RunPython(
                    'force_text',
                    tools.Concat(
                        tools.Try(ctx['record']['header']['setSpec']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:type']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:format']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:subject']),
                    )
                )
            )
        )
    )

    tags = tools.Map(
        tools.Delegate(OAIThroughTags),
        tools.Concat(
            tools.Map(
                tools.RunPython('tokenize'),
                tools.RunPython(
                    'force_text',
                    tools.Concat(
                        tools.Try(ctx['record']['header']['setSpec']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:type']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:format']),
                        tools.Try(ctx['record']['metadata']['dc']['dc:subject']),
                    )
                )
            ),
            deep=True
        )
    )

    date_updated = tools.ParseDate(ctx['record']['header']['datestamp'])

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        # An agent responsible for making contributions to the resource.
        contributor = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:contributor')

        # The spatial or temporal topic of the resource, the spatial applicability of the resource,
        # or the jurisdiction under which the resource is relevant.
        coverage = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:coverage')

        # An agent primarily responsible for making the resource.
        creator = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:creator')

        # A point or period of time associated with an event in the lifecycle of the resource.
        dates = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:date')

        # The file format, physical medium, or dimensions of the resource.
        resource_format = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:format')

        # An unambiguous reference to the resource within a given context.
        identifiers = tools.Concat(
            tools.Try(ctx['record']['metadata']['dc']['dc:identifier']),
            tools.Try(ctx['record']['header']['identifier'])
        )

        # A related resource.
        relation = tools.RunPython('get_relation', ctx)

        # A related resource from which the described resource is derived.
        source = tools.Maybe(tools.Maybe(ctx['record'], 'metadata')['dc'], 'dc:source')

        # The nature or genre of the resource.
        resource_type = tools.Try(ctx.record.metadata.dc['dc:type'])

        set_spec = tools.Maybe(ctx.record.header, 'setSpec')

        # Language also stored in the Extra class in case the language reported cannot be parsed by ParseLanguage
        language = tools.Try(ctx.record.metadata.dc['dc:language'])

        # Status in the header, will exist if the resource is deleted
        status = tools.Maybe(ctx.record.header, '@status')

    def get_schema(self, types):
        if not types or not self.type_map:
            return self.default_type
        if isinstance(types, str):
            types = [types]
        for t in types:
            if t in self.type_map:
                return self.type_map[t]
        return self.default_type

    def force_text(self, data):
        if isinstance(data, dict):
            return data['#text']

        if isinstance(data, str):
            return data

        fixed = []
        for datum in (data or []):
            if datum is None:
                continue
            if isinstance(datum, dict):
                if '#text' not in datum:
                    logger.warn('Skipping %s, no #text key exists', datum)
                    continue
                fixed.append(datum['#text'])
            elif isinstance(datum, str):
                fixed.append(datum)
            else:
                raise Exception(datum)
        return fixed

    def tokenize(self, data):
        if isinstance(data, str):
            data = [data]
        tokens = []
        for item in data:
            tokens.extend([x.strip() for x in re.split(r'(?: - )|\.|,', item) if x])
        return tokens

    def get_relation(self, ctx):
        if not ctx['record'].get('metadata'):
            return []
        relation = ctx['record']['metadata']['dc'].get('dc:relation', [])
        if isinstance(relation, dict):
            return relation['#text']
        return relation


class OAINormalizer(Normalizer):

    @property
    def root_parser(self):
        parser = OAICreativeWork
        parser.default_type = self.config.emitted_type.lower()
        parser.type_map = self.config.type_map

        if self.config.property_list:
            logger.debug('Attaching addition properties %s to normalizer for %s'.format(self.config.property_list, self.config.label))
            for prop in self.config.property_list:
                if prop in parser._extra:
                    logger.warning('Skipping property %s, it already exists', prop)
                    continue
                parser._extra[prop] = tools.Try(ctx.record.metadata.dc['dc:' + prop]).chain()[0]

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
