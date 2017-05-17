import re
import logging
from lxml import etree

from share.transform.chain import ctx, ChainTransformer, links as tools
from share.transform.chain.parsers import Parser
from share.transform.chain.utils import force_text


logger = logging.getLogger(__name__)


def not_citation(identifier):
    return re.search(r'(pp\. \d+\-\d+.)|(ISSN )|( +\(\d\d\d\d\))', identifier) is None


class OAIAgent(Parser):
    schema = tools.GuessAgentType(ctx)

    name = ctx


class OAIAgentIdentifier(Parser):
    schema = 'AgentIdentifier'

    uri = ctx


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

    identifiers = tools.Map(tools.Delegate(OAIWorkIdentifier), ctx)

    class Extra:
        identifier = ctx


class OAIWorkRelation(Parser):
    schema = 'WorkRelation'

    related = tools.Delegate(OAIRelatedWork, ctx)


class OAIAgentWorkRelation(Parser):
    schema = 'AgentWorkRelation'

    agent = tools.Delegate(OAIAgent, tools.RunPython(force_text, ctx))
    cited_as = tools.RunPython(force_text, ctx)


class OAIContributor(OAIAgentWorkRelation):
    schema = 'Contributor'


class OAICreator(OAIContributor):
    schema = 'Creator'

    order_cited = ctx('index')


class OAIPublisher(Parser):
    schema = 'Publisher'

    agent = tools.Delegate(OAIAgent.using(schema=tools.GuessAgentType(ctx, default='organization')), ctx)


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

    title = tools.Join(tools.RunPython(force_text, tools.Try(ctx.record.metadata.dc['dc:title'])))
    description = tools.Join(tools.RunPython(force_text, tools.Try(ctx.record.metadata.dc['dc:description'])))

    identifiers = tools.Map(
        tools.Delegate(OAIWorkIdentifier),
        tools.Unique(tools.Map(
            tools.Try(tools.IRI(), exceptions=(ValueError, )),
            tools.Filter(
                not_citation,
                tools.RunPython(
                    force_text,
                    tools.Concat(
                        tools.Try(ctx.record.metadata.dc['dc:identifier']),
                        tools.Try(ctx.record.header['identifier'])
                    )
                )
            )
        ))
    )

    related_works = tools.Concat(
        tools.Map(
            tools.Delegate(OAIWorkRelation),
            tools.Unique(tools.Map(
                tools.Try(tools.IRI(), exceptions=(ValueError, )),
                tools.RunPython('get_relation', ctx)
            ))
        )
    )

    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(OAICreator),
            tools.Try(ctx.record.metadata.dc['dc:creator'])
        ),
        tools.Map(
            tools.Delegate(OAIContributor),
            tools.Try(ctx.record.metadata.dc['dc:contributor'])
        ),
        tools.Map(
            tools.Delegate(OAIPublisher),
            tools.RunPython(force_text, tools.Try(ctx.record.metadata.dc['dc:publisher']))
        ),
    )

    rights = tools.Join(tools.Try(ctx.record.metadata.dc['dc:rights']))

    # Note: this is only taking the first language in the case of multiple languages
    language = tools.ParseLanguage(
        tools.Try(ctx.record.metadata.dc['dc:language'][0]),
    )

    subjects = tools.Map(
        tools.Delegate(OAIThroughSubjects),
        tools.Subjects(
            tools.Map(
                tools.RunPython('tokenize'),
                tools.RunPython(
                    force_text,
                    tools.Concat(
                        tools.Try(ctx.record.header.setSpec),
                        tools.Try(ctx.record.metadata.dc['dc:type']),
                        tools.Try(ctx.record.metadata.dc['dc:format']),
                        tools.Try(ctx.record.metadata.dc['dc:subject']),
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
                    force_text,
                    tools.Concat(
                        tools.Try(ctx.record.header.setSpec),
                        tools.Try(ctx.record.metadata.dc['dc:type']),
                        tools.Try(ctx.record.metadata.dc['dc:format']),
                        tools.Try(ctx.record.metadata.dc['dc:subject']),
                    )
                )
            ),
            deep=True
        )
    )

    date_updated = tools.ParseDate(ctx.record.header.datestamp)

    is_deleted = tools.RunPython('check_status', tools.Try(ctx.record.header['@status']))

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        # An agent responsible for making contributions to the resource.
        contributor = tools.Try(ctx.record.metadata.dc['dc:contributor'])

        # The spatial or temporal topic of the resource, the spatial applicability of the resource,
        # or the jurisdiction under which the resource is relevant.
        coverage = tools.Try(ctx.record.metadata.dc['dc:coverage'])

        # An agent primarily responsible for making the resource.
        creator = tools.Try(ctx.record.metadata.dc['dc:creator'])

        # A point or period of time associated with an event in the lifecycle of the resource.
        dates = tools.Try(ctx.record.metadata.dc['dc:date'])

        # The file format, physical medium, or dimensions of the resource.
        resource_format = tools.Try(ctx.record.metadata.dc['dc:format'])

        # An unambiguous reference to the resource within a given context.
        identifiers = tools.Concat(
            tools.Try(ctx.record.metadata.dc['dc:identifier']),
            tools.Try(ctx.record.header['identifier'])
        )

        # A related resource.
        relation = tools.RunPython('get_relation', ctx)

        # A related resource from which the described resource is derived.
        source = tools.Try(ctx.record.metadata.dc['dc:source'])

        # The nature or genre of the resource.
        resource_type = tools.Try(ctx.record.metadata.dc['dc:type'])

        set_spec = tools.Try(ctx.record.header.setSpec)

        # Language also stored in the Extra class in case the language reported cannot be parsed by ParseLanguage
        language = tools.Try(ctx.record.metadata.dc['dc:language'])

        # Status in the header, will exist if the resource is deleted
        status = tools.Try(ctx.record.header['@status'])

    def check_status(self, status):
        if status == 'deleted':
            return True
        return False

    def get_schema(self, types):
        if not types or not self.type_map:
            return self.default_type
        if isinstance(types, str):
            types = [types]
        for t in types:
            if isinstance(t, dict):
                t = t['#text']
            t = t.lower()
            if t in self.type_map:
                return self.type_map[t]
        return self.default_type

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
        relation = ctx['record']['metadata']['dc'].get('dc:relation') or []
        identifiers = ctx['record']['metadata']['dc'].get('dc:identifier') or []
        if isinstance(identifiers, dict):
            identifiers = (identifiers, )
        identifiers = ''.join(i['#text'] if isinstance(i, dict) else i for i in identifiers if i)

        identifiers = re.sub('http|:|/', '', identifiers + ctx['record']['header']['identifier'])

        if isinstance(relation, dict):
            relation = (relation['#text'], )

        return [r for r in relation if r and re.sub('http|:|/', '', r) not in identifiers]


class OAITransformer(ChainTransformer):
    """Transformer for oai_dc metadata format.

    transformer_kwargs (TODO explain):
        emitted_type
        property_list
        approved_sets
        type_map
    """

    VERSION = 1

    def get_root_parser(self, _):
        class RootParser(OAICreativeWork):
            default_type = self.kwargs.get('emitted_type', 'creativework').lower()
            type_map = {
                **{r.lower(): r for r in self.allowed_roots},
                **{t.lower(): v for t, v in self.kwargs.get('type_map', {}).items()}
            }

        property_list = self.kwargs.get('property_list')
        if property_list:
            logger.debug('Attaching addition properties %s to transformer for %s'.format(property_list, self.config.label))
            for prop in property_list:
                if prop in RootParser._extra:
                    logger.warning('Skipping property %s, it already exists', prop)
                    continue
                RootParser._extra[prop] = tools.Try(ctx.record.metadata.dc['dc:' + prop]).chain()[0]

        return RootParser

    def do_transform(self, data):
        approved_sets = self.kwargs.get('approved_sets')
        if approved_sets is not None:
            specs = set(x.replace('publication:', '') for x in etree.fromstring(data).xpath(
                'ns0:header/ns0:setSpec/node()',
                namespaces={'ns0': 'http://www.openarchives.org/OAI/2.0/'}
            ))
            if not (specs & set(approved_sets)):
                logger.warning('Series %s not found in approved_sets for %s', specs, self.config.label)
                return (None, None)

        return super().do_transform(data)
