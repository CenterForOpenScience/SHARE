import re
import logging
from lxml import etree

import xmltodict

from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer


logger = logging.getLogger(__name__)


def force_text(data):
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


def not_invalid(identifier):
    if 'invalid' in identifier:
        return False
    return True


class AffiliatedAgent(Parser):
    schema = tools.GuessAgentType(ctx, default='organization')

    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AffiliatedAgent, ctx)


# TODO
class MODSAgent(Parser):
    """
    @type
        personal – Indicates the name is that of a person.
        corporate – Indicates the name is that of a company, institution, or other organization.
        conference – Indicates the name is that of a conference or related type of meeting.
        family – Indicates the name is that of a family.
    """
    # should choose default based on type
    schema = tools.GuessAgentType(
        tools.RunPython(force_text, tools.Try(ctx['mods:displayForm']))
    )

    # may need to check for something else if displayForm isn't there
    name = tools.Try(tools.RunPython(force_text, ctx['mods:displayForm']))

    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), tools.Concat(tools.Try(
        tools.Filter(lambda x: bool(x), tools.RunPython(force_text, ctx['mods:affiliation']))
    )))

    class Extra:
        name_type = tools.Try(ctx['@type'])
        name_part = tools.Try(ctx['mods:namePart'])
        affiliation = tools.Try(ctx['mods:affiliation'])
        description = tools.Try(ctx['mods:description'])
        display_form = tools.Try(ctx['mods:displayForm'])
        etal = tools.Try(ctx['mods:etal'])
        name_identifier = tools.Try(ctx['mods:nameIdentifier'])


class MODSAgentIdentifier(Parser):
    schema = 'AgentIdentifier'

    uri = ctx


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


class MODSRelatedWork(Parser):
    schema = 'CreativeWork'

    identifiers = tools.Map(tools.Delegate(MODSWorkIdentifier), ctx)

    class Extra:
        identifier = ctx


class MODSWorkRelation(Parser):
    schema = 'WorkRelation'

    def get_creative_work(self):
        return MODSCreativeWork

    related = tools.Delegate(get_creative_work, ctx)


class MODSAgentWorkRelation(Parser):
    schema = 'AgentWorkRelation'

    agent = tools.Delegate(MODSAgent, ctx)
    cited_as = tools.RunPython(force_text, tools.Try(ctx['mods:displayForm']))


class MODSContributor(MODSAgentWorkRelation):
    schema = 'Contributor'


class MODSCreator(MODSContributor):
    schema = 'Creator'

    order_cited = ctx('index')


class MODSPublisher(Parser):
    schema = 'Publisher'

    agent = tools.Delegate(MODSAgent.using(schema=tools.GuessAgentType(ctx, default='organization')), ctx)


class MODSCreativeWork(Parser):
    default_type = 'CreativeWork'
    type_map = None

    schema = tools.RunPython(
        'get_schema',
        tools.OneOf(
            tools.RunPython(force_text, ctx['mods:genre']),
            tools.Static(None)
        )
    )

    title = tools.Join(tools.RunPython(force_text, tools.Try(ctx['mods:titleInfo']['mods:title'])))

    # TODO
    # This attribute is used with shareable="no" for data that may be proprietary or is rights
    # protected and should not be used outside of a local system (such as providing to harvesters).
    description = tools.Join(tools.RunPython(force_text, tools.Try(ctx['mods:abstract'])))

    # do we want isbns?
    identifiers = tools.Map(
        tools.Delegate(MODSWorkIdentifier),
        tools.Unique(tools.Map(
            tools.Try(tools.IRI(), exceptions=(ValueError, )),
            tools.RunPython(
                force_text,
                tools.Filter(
                    not_invalid,
                    tools.Concat(
                        tools.Try(ctx['mods:identifier']),
                        tools.Try(ctx.header['identifier'])
                    )
                )
            ))
        )
    )

    related_works = tools.Concat(
        tools.Map(
            tools.Delegate(MODSWorkRelation),
            tools.Try(ctx['mods:relatedItem'])
        )
    )

    # TODO: separate creators
    """
    Subelement: <role><roleTerm>
        fnd   Funder
        hst   Host
        his   Host institution
        pbl   Publisher
        cre   Creator
        ctb   Contributor
        aut   Author
        aud   Author of dialog
        aui   Author of introduction, etc.
        aqt   Author in quotations or text abstracts
        aft   Author of afterword, colophon, etc.
    """
    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(MODSContributor),
            tools.Try(ctx['mods:name'])
        ),
        tools.Map(
            tools.Delegate(MODSPublisher),
            tools.Try(ctx['mods:originInfo']['mods:publisher'])
        ),
    )

    rights = tools.Try(ctx['mods:accessCondition'])

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
                tools.RunPython(
                    force_text,
                    tools.Concat(
                        tools.Try(ctx.header.setSpec),
                        tools.Try(ctx['mods:genre']),
                        tools.Try(ctx['mods:classification']),
                        tools.Try(ctx['mods:subject']['mods:topic']),
                    )
                )
            ),
            deep=True
        )
    )

    date_updated = tools.ParseDate(tools.Try(ctx.header.datestamp))
    date_published = tools.RunPython(
        force_text,
        tools.Try(ctx['mods:originInfo']['mods:dateIssued'])
    )

    is_deleted = tools.RunPython('check_status', tools.Try(ctx.record.header['@status']))

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

    def check_status(self, status):
        if status == 'deleted':
            return True
        return False

    # TODO
    # should check current models if no type map is given
    # either use registries attribute of abstractcreativework or check if model exists
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


class MODSNormalizer(Normalizer):

    @property
    def root_parser(self):
        class RootParser(MODSCreativeWork):
            default_type = self.config.emitted_type.lower()
            type_map = {
                **{r.lower(): r for r in self.allowed_roots},
                **{t.lower(): v for t, v in self.config.type_map.items()}
            }

        return RootParser

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

    def unwrap_data(self, data):
        unwrapped_data = xmltodict.parse(data, process_namespaces=True, namespaces=self.namespaces)

        flattened_data = {}
        flattened_data['header'] = unwrapped_data['record']['header']
        top_level_fields = [
            'mods:abstract',
            'mods:accessCondition',
            'mods:classification',
            'mods:extension',
            'mods:genre',
            'mods:identifier',
            'mods:language',
            'mods:location',
            'mods:name',
            'mods:note',
            'mods:originInfo',
            'mods:part',
            'mods:physicalDescription',
            'mods:recordInfo',
            'mods:relatedItem',
            'mods:subject',
            'mods:tableOfContents',
            'mods:targetAudience',
            'mods:titleInfo',
            'mods:typeOfResource'
        ]

        for field in top_level_fields:
            if field in unwrapped_data['record']['metadata']['mods:mods']:
                flattened_data[field] = unwrapped_data['record']['metadata']['mods:mods'][field]

        return flattened_data
