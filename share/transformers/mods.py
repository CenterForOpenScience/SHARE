import re
import logging
from lxml import etree

import xmltodict

from share.transform.chain import ChainTransformer, ctx, links as tools
from share.transform.chain.links import GuessAgentTypeLink
from share.transform.chain.parsers import Parser
from share.transform.chain.utils import force_text


logger = logging.getLogger(__name__)


def get_list(dct, key):
    val = dct.get(key, [])
    return val if isinstance(val, list) else [val]


class AffiliatedAgent(Parser):
    schema = tools.GuessAgentType(ctx, default='organization')

    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AffiliatedAgent, ctx)


class MODSAgentIdentifier(Parser):
    schema = 'AgentIdentifier'

    uri = ctx


class MODSAgent(Parser):
    schema = tools.RunPython('get_agent_schema', ctx)

    name = tools.OneOf(
        tools.RunPython(force_text, ctx['mods:displayForm']),
        tools.RunPython('squash_name_parts', ctx)
    )

    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), tools.Concat(tools.Try(
        tools.Filter(lambda x: bool(x), tools.RunPython(force_text, ctx['mods:affiliation']))
    )))

    identifiers = tools.Map(
        tools.Delegate(MODSAgentIdentifier),
        tools.Unique(tools.Map(
            tools.Try(tools.IRI(), exceptions=(ValueError, )),
            tools.Map(
                tools.RunPython(force_text),
                tools.Filter(
                    lambda obj: 'invalid' not in obj,
                    tools.Try(ctx['mods:nameIdentifier']),
                )
            )
        ))
    )

    class Extra:
        name_type = tools.Try(ctx['@type'])
        name_part = tools.Try(ctx['mods:namePart'])
        affiliation = tools.Try(ctx['mods:affiliation'])
        description = tools.Try(ctx['mods:description'])
        display_form = tools.Try(ctx['mods:displayForm'])
        etal = tools.Try(ctx['mods:etal'])
        name_identifier = tools.Try(ctx['mods:nameIdentifier'])

    def squash_name_parts(self, name):
        name_parts = get_list(name, 'mods:namePart')
        return ' '.join([force_text(n) for n in name_parts])

    def get_agent_schema(self, obj):
        name_type = obj.get('@type')
        if name_type == 'personal':
            return 'person'
        if name_type == 'conference':
            return 'organization'
        # TODO SHARE-718
        # if name_type == 'family':
        #    return 'family'
        if name_type == 'corporate':
            return GuessAgentTypeLink(default='organization').execute(self.squash_name_parts(obj))
        return GuessAgentTypeLink().execute(self.squash_name_parts(obj))


class MODSPersonSplitName(MODSAgent):
    schema = 'person'

    name = None
    family_name = tools.RunPython('get_name_part', ctx, 'family')
    given_name = tools.RunPython('get_name_part', ctx, 'given')
    suffix = tools.RunPython('get_name_part', ctx, 'termsOfAddress')

    def get_name_part(self, obj, type):
        name_parts = get_list(obj, 'mods:namePart')
        return ' '.join([force_text(n) for n in name_parts if n.get('@type') == type])


class MODSWorkIdentifier(Parser):
    schema = 'WorkIdentifier'

    uri = ctx


class MODSSubject(Parser):
    schema = 'Subject'

    name = ctx


class MODSThroughSubjects(Parser):
    schema = 'ThroughSubjects'

    subject = tools.Delegate(MODSSubject, ctx)


class MODSTag(Parser):
    schema = 'Tag'

    name = ctx


class MODSThroughTags(Parser):
    schema = 'ThroughTags'

    tag = tools.Delegate(MODSTag, ctx)


def work_parser(_):
    return type(next(p for p in ctx.parsers if isinstance(p, MODSCreativeWork)))


class MODSWorkRelation(Parser):
    schema = 'WorkRelation'

    related = tools.Delegate(work_parser, ctx)


def agent_parser(name):
    name_parts = get_list(name, 'mods:namePart')
    split_name = any(isinstance(n, dict) and n.get('@type') in {'given', 'family'} for n in name_parts)
    return MODSPersonSplitName if split_name else MODSAgent


class MODSAgentWorkRelation(Parser):
    schema = 'AgentWorkRelation'

    agent = tools.Delegate(agent_parser, ctx)
    cited_as = tools.RunPython(force_text, tools.Try(ctx['mods:displayForm']))


class MODSHost(MODSAgentWorkRelation):
    schema = 'Host'


class MODSFunder(MODSAgentWorkRelation):
    schema = 'Funder'


class MODSContributor(MODSAgentWorkRelation):
    schema = 'Contributor'


class MODSCreator(MODSContributor):
    schema = 'Creator'

    order_cited = ctx('index')


class MODSPublisher(MODSAgentWorkRelation):
    schema = 'Publisher'

    agent = tools.Delegate(MODSAgent.using(schema=tools.GuessAgentType(ctx, default='organization')), ctx)


class MODSSimpleAgent(Parser):
    schema = tools.GuessAgentType(ctx, default='organization')

    name = ctx


class MODSSimplePublisher(Parser):
    schema = 'Publisher'

    agent = tools.Delegate(MODSSimpleAgent, ctx)


class MODSCreativeWork(Parser):
    default_type = 'CreativeWork'
    type_map = None
    role_map = None

    schema = tools.RunPython(
        'get_schema',
        tools.OneOf(
            tools.RunPython(force_text, ctx['mods:genre']),
            tools.Static(None)
        )
    )

    title = tools.RunPython('join_title_info', ctx)

    # Abstracts have the optional attribute "shareable". Don't bother checking for it, because
    # abstracts that are not shareable should not have been shared with SHARE.
    description = tools.Join(tools.RunPython(force_text, tools.Try(ctx['mods:abstract'])))

    identifiers = tools.Map(
        tools.Delegate(MODSWorkIdentifier),
        tools.Unique(tools.Map(
            tools.Try(tools.IRI(), exceptions=(ValueError, )),
            tools.Map(
                tools.RunPython(force_text),
                tools.Filter(
                    lambda obj: 'invalid' not in obj,
                    tools.Concat(
                        tools.Try(ctx['mods:identifier']),
                        tools.Try(ctx.header['identifier'])
                    )
                )
            )
        ))
    )

    related_works = tools.Concat(
        tools.Map(
            tools.Delegate(MODSWorkRelation),
            tools.Try(ctx['mods:relatedItem'])
        )
    )

    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(MODSCreator),
            tools.RunPython('filter_names', ctx, 'creator')
        ),
        tools.Map(
            tools.Delegate(MODSFunder),
            tools.RunPython('filter_names', ctx, 'funder')
        ),
        tools.Map(
            tools.Delegate(MODSHost),
            tools.RunPython('filter_names', ctx, 'host')
        ),
        tools.Map(
            tools.Delegate(MODSPublisher),
            tools.RunPython('filter_names', ctx, 'publisher')
        ),
        tools.Map(
            tools.Delegate(MODSContributor),
            tools.RunPython('filter_names', ctx, 'creator', 'funder', 'host', 'publisher', invert=True)
        ),
        tools.Map(
            tools.Delegate(MODSSimplePublisher),
            tools.Try(ctx['mods:originInfo']['mods:publisher']),
        ),
    )

    rights = tools.RunPython(force_text, tools.Try(ctx['mods:accessCondition']))

    language = tools.ParseLanguage(
        tools.Try(ctx['mods:language']['mods:languageTerm']),
    )

    subjects = tools.Map(
        tools.Delegate(MODSThroughSubjects),
        tools.Subjects(
            tools.Concat(
                tools.Try(ctx['mods:subject']['mods:topic']),
            )
        )
    )

    tags = tools.Map(
        tools.Delegate(MODSThroughTags),
        tools.Concat(
            tools.Map(
                tools.RunPython('tokenize'),
                tools.Map(
                    tools.RunPython(force_text),
                    tools.Try(ctx.header.setSpec),
                    tools.Try(ctx['mods:genre']),
                    tools.Try(ctx['mods:classification']),
                    tools.Try(ctx['mods:subject']['mods:topic']),
                )
            ),
            deep=True
        )
    )

    date_updated = tools.ParseDate(tools.Try(ctx.header.datestamp))

    # TODO (in regulator) handle date ranges, uncertain dates ('1904-1941', '1890?', '1980-', '19uu', etc.)
    date_published = tools.OneOf(
        tools.ParseDate(tools.RunPython(force_text, tools.Try(ctx['mods:originInfo']['mods:dateIssued']))),
        tools.Static(None)
    )

    is_deleted = tools.RunPython(lambda status: status == 'deleted', tools.Try(ctx.record.header['@status']))

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """

        # (dc:description) http://www.loc.gov/standards/mods/userguide/abstract.html
        abstract = tools.Try(ctx['mods:abstract'])

        # (dc:rights) http://www.loc.gov/standards/mods/userguide/accesscondition.html
        accessConditions = tools.Try(ctx['mods:accessCondition'])

        # (dc:subject) http://www.loc.gov/standards/mods/userguide/classification.html
        classification = tools.Try(ctx['mods:classification'])

        # (N/A) http://www.loc.gov/standards/mods/userguide/extension.html
        extension = tools.Try(ctx['mods:extension'])

        # SHARE type
        # (dc:type) http://www.loc.gov/standards/mods/userguide/genre.html
        genre = tools.Try(ctx['mods:genre'])

        # (dc:identifier) http://www.loc.gov/standards/mods/userguide/identifier.html
        identifier = tools.Try(ctx['mods:identifier'])

        # (dc:language) http://www.loc.gov/standards/mods/userguide/language.html
        language = tools.Try(ctx['mods:language'])

        # (dc:identifier for url) http://www.loc.gov/standards/mods/userguide/location.html
        location = tools.Try(ctx['mods:location'])

        # (dc:creator|dc:contributor) http://www.loc.gov/standards/mods/userguide/name.html
        name = tools.Try(ctx['mods:name'])

        # (dc:description) http://www.loc.gov/standards/mods/userguide/note.html
        note = tools.Try(ctx['mods:note'])

        # (dc:publisher|dc:date) http://www.loc.gov/standards/mods/userguide/origininfo.html
        originInfo = tools.Try(ctx['mods:originInfo'])

        # Extra
        # (dc:title) http://www.loc.gov/standards/mods/userguide/part.html
        part = tools.Try(ctx['mods:part'])

        # (dc:format or N/A) http://www.loc.gov/standards/mods/userguide/physicaldescription.html
        physicalDescription = tools.Try(ctx['mods:physicalDescription'])

        # Metadata information
        # (N/A) http://www.loc.gov/standards/mods/userguide/recordinfo.html
        recordInfo = tools.Try(ctx['mods:recordInfo'])

        # (dc:relation) http://www.loc.gov/standards/mods/userguide/relateditem.html
        relatedItem = tools.Try(ctx['mods:relatedItem'])

        # (dc:subject|dc:type|dc:coverage|N/A) http://www.loc.gov/standards/mods/userguide/subject.html
        subject = tools.Try(ctx['mods:subject'])

        # (dc:description) http://www.loc.gov/standards/mods/userguide/tableofcontents.html
        tableOfContents = tools.Try(ctx['mods:tableOfContents'])

        # (N/A) http://www.loc.gov/standards/mods/userguide/targetaudience.html
        targetAudience = tools.Try(ctx['mods:targetAudience'])

        # (dc:title) http://www.loc.gov/standards/mods/userguide/titleinfo.html
        titleInfo = tools.Try(ctx['mods:titleInfo'])

        # Extra
        # (dc:type) http://www.loc.gov/standards/mods/userguide/typeofresource.html
        typeOfResource = tools.Try(ctx['mods:typeOfResource'])

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

    # Map titleInfos to a string: https://www.loc.gov/standards/mods/userguide/titleinfo.html#mappings
    def join_title_info(self, obj):
        def get_part(title_info, part_name, delimiter=''):
            part = force_text(title_info.get(part_name, '')).strip()
            return delimiter + part if part else ''

        title_infos = get_list(obj, 'mods:titleInfo')
        titles = []
        for title_info in title_infos:
            title = ''
            title += get_part(title_info, 'mods:nonSort')
            title += get_part(title_info, 'mods:title')
            title += get_part(title_info, 'mods:subTitle', ': ')
            title += get_part(title_info, 'mods:partNumber', '. ')
            title += get_part(title_info, 'mods:partName', ': ')
            if title:
                titles.append(title)
        return '. '.join(titles)

    def filter_names(self, obj, *roles, invert=False):
        names = get_list(obj, 'mods:name')
        filtered = [*names] if invert else []
        for name in names:
            name_roles = get_list(name, 'mods:role')
            for role in name_roles:
                role_terms = get_list(role, 'mods:roleTerm')
                name_roles = {force_text(r).lower() for r in role_terms}
                name_roles.update({self.role_map[r] for r in name_roles if r in self.role_map})
                if name_roles.intersection(roles):
                    if invert:
                        filtered.remove(name)
                    else:
                        filtered.append(name)
        return filtered


class MODSTransformer(ChainTransformer):
    VERSION = 1

    marc_roles = {
        'fnd': 'funder',
        'hst': 'host',
        'his': 'host',
        'pbl': 'publisher',
        'cre': 'creator',
        'aut': 'creator',
        'author': 'creator',
    }

    def get_root_parser(self, _):
        class RootParser(MODSCreativeWork):
            default_type = self.kwargs.get('emitted_type', 'creativework').lower()
            type_map = {
                **{r.lower(): r for r in self.allowed_roots},
                **{t.lower(): v for t, v in self.kwargs.get('type_map', {}).items()}
            }
            role_map = {
                **{k: v for k, v in self.marc_roles.items()},
                **{k.lower(): v.lower() for k, v in self.kwargs.get('role_map', {}).items()}
            }

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

    def unwrap_data(self, data):
        unwrapped_data = xmltodict.parse(data, process_namespaces=True, namespaces=self.kwargs.get('namespaces', self.NAMESPACES))
        return {
            **unwrapped_data['record'].get('metadata', {}).get('mods:mods', {}),
            'header': unwrapped_data['record']['header'],
        }
