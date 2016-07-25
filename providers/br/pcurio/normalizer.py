import re

from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize import Normalizer
from share.normalize.utils import format_doi_as_url


URL_REGEX = re.compile(r'(https?:\/\/\S*\.[^\s\[\]\<\>\}\{\^]*)')
DOI_REGEX = re.compile(r'(doi:10\.\S*)')


class Link(Parser):

    url = tools.RunPython('format_link', ctx)
    type = tools.RunPython('get_link_type', ctx)

    # TODO: account for other types of links
    # i.e. ISBN

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if self.config.home_page and self.config.home_page in link:
            return 'provider'
        return 'misc'

    def format_link(self, link):
        link_type = self.get_link_type(link)
        if link_type == 'doi':
            if 'http' in link:
                return link
            return format_doi_as_url(self, link)
        return link


class ThroughLinks(Parser):

    link = tools.Delegate(Link, ctx)


class Person(Parser):

    suffix = tools.ParseName(ctx).suffix
    family_name = tools.ParseName(ctx).last
    given_name = tools.ParseName(ctx).first
    additional_name = tools.ParseName(ctx).middle


class Contributor(Parser):

    person = tools.Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Publisher(Parser):
    name = ctx


class Institution(Parser):
    name = ctx


class Organization(Parser):
    name = ctx


class Association(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class CreativeWork(Parser):
    ORGANIZATION_KEYWORDS = (
        'the',
        'center'
    )
    INSTITUTION_KEYWORDS = (
        'school',
        'university',
        'institution',
        'institute'
    )

    title = tools.Join(
        tools.Map(
            tools.RunPython('strip_language'),
            tools.Map(
                tools.RunPython('force_text'),
                tools.Try(ctx.record.metadata['oaidc:dc'].title)
            )
        )
    )

    description = tools.Try(ctx.record.metadata['oaidc:dc'].description)

    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        tools.Try(ctx.record.metadata['oaidc:dc'].publisher)
    )

    rights = tools.Join(tools.Try(ctx.record.metadata['oaidc:dc'].rights))

    # Note: this is only taking the first language in the case of multiple languages
    language = tools.ParseLanguage(
        tools.Try(ctx.record.metadata['oaidc:dc'].language[0]),
    )

    contributors = tools.Map(
        tools.Delegate(Contributor),
        tools.RunPython(
            'get_contributors',
            tools.Concat(
                tools.Try(ctx.record.metadata['oaidc:dc'].creator),
                tools.Try(ctx.record.metadata['oaidc:dc'].contributor)
            ),
            'contributor'
        )
    )

    institutions = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Institution))),
        tools.RunPython(
            'get_contributors',
            tools.Concat(
                tools.Try(ctx.record.metadata['oaidc:dc'].creator),
                tools.Try(ctx.record.metadata['oaidc:dc'].contributor)
            ),
            'institution'
        )
    )

    organizations = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Organization))),
        tools.RunPython(
            'get_contributors',
            tools.Concat(
                tools.Try(ctx.record.metadata['oaidc:dc'].creator),
                tools.Try(ctx.record.metadata['oaidc:dc'].contributor)
            ),
            'organization'
        )
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Map(
            tools.RunPython('strip_language'),
            tools.Map(
                tools.RunPython('force_text'),
                tools.Try(ctx.record.metadata['oaidc:dc'].type),
                tools.Try(ctx.record.metadata['oaidc:dc'].subject),
            )
        )
    )

    links = tools.Map(
        tools.Delegate(ThroughLinks),
        tools.RunPython(
            'get_links',
            tools.Concat(
                tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'relation'),
                tools.Map(tools.RunPython('fix_escapes'), tools.Try(ctx.record.metadata['oaidc:dc']['identifier'])),
            )
        )
    )

    date_updated = tools.ParseDate(ctx.record.header.datestamp)

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        # An entity responsible for making contributions to the resource.
        contributor = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'contributor')

        # The spatial or temporal topic of the resource, the spatial applicability of the resource,
        # or the jurisdiction under which the resource is relevant.
        coverage = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'coverage')

        # An entity primarily responsible for making the resource.
        creator = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'creator')

        # A point or period of time associated with an event in the lifecycle of the resource.
        dates = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'date')

        # An unambiguous reference to the resource within a given context.
        identifiers = tools.Concat(
            tools.Try(ctx.record.metadata['oaidc:dc']['identifier']),
            tools.Maybe(ctx.record.header, 'identifier')
        )

        # A related resource.
        relation = tools.RunPython('get_relation', ctx)

        # A related resource from which the described resource is derived.
        source = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'source')

        # The topic of the resource.
        subject = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'subject')

        # The nature or genre of the resource.
        resource_type = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'type')

        # Language also stored in the Extra class in case the language reported cannot be parsed by ParseLanguage
        language = tools.Maybe(tools.Maybe(ctx.record, 'metadata')['oaidc:dc'], 'language')

        # Status in the header, will exist if the resource is deleted
        status = tools.Maybe(ctx.record.header, '@status')

    def fix_escapes(self, link):
        return link.replace('&amp', '&')

    def strip_language(self, string):
        return re.sub(r'^\[\w\w\] ', '', string, count=1)

    def get_links(self, ctx):
        links = []
        for link in ctx:
            if link:
                try:
                    found_url = URL_REGEX.search(link).group()
                    links.append(found_url)
                    continue
                except AttributeError:
                    pass
                try:
                    found_doi = DOI_REGEX.search(link).group()
                    if 'dx.doi.org' in found_doi:
                        links.append(found_doi)
                    else:
                        links.append('http://dx.doi.org/{}'.format(found_doi.replace('doi:', '')))
                except AttributeError:
                    continue
        return links

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
                fixed.append(datum['#text'])
            elif isinstance(datum, str):
                fixed.append(datum)
            else:
                raise Exception(datum)
        return fixed

    def get_relation(self, ctx):
        metadata = ctx['record'].get('metadata', None)
        if metadata:
            base = ctx['record']['metadata']['oaidc:dc']
            try:
                base['relation']
            except KeyError:
                return []
            else:
                try:
                    base['relation']['#text']
                except TypeError:
                    return base['relation']
        else:
            return []

    def get_contributors(self, options, entity):
        """
        Returns list of organization, institutions, or contributors names based on entity type.
        """
        if entity == 'organization':
            organizations = [
                value for value in options if
                (
                    value and
                    not self.list_in_string(value, self.INSTITUTION_KEYWORDS) and
                    self.list_in_string(value, self.ORGANIZATION_KEYWORDS)
                )
            ]
            return organizations
        elif entity == 'institution':
            institutions = [
                value for value in options if
                (
                    value and
                    self.list_in_string(value, self.INSTITUTION_KEYWORDS)
                )
            ]
            return institutions
        elif entity == 'contributor':
            people = [
                value for value in options if
                (
                    value and
                    not self.list_in_string(value, self.INSTITUTION_KEYWORDS) and not
                    self.list_in_string(value, self.ORGANIZATION_KEYWORDS)
                )
            ]
            return people
        else:
            return options

    def list_in_string(self, string, list_):
        if any(word in string.lower() for word in list_):
            return True
        return False


class Normalizer(Normalizer):
    root_parser = CreativeWork
