import re

from share.normalize import ctx, tools
from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer

THE_REGEX = re.compile(r'(^the\s|\sthe\s)')


class Link(Parser):

    url = ctx
    type = tools.Static('url')


class ProviderLink(Parser):

    schema = 'Link'

    url = ctx
    type = tools.Static('provider')


class ThroughLinks(Parser):

    link = tools.Delegate(Link, ctx)


class ProviderThroughLinks(Parser):

    schema = 'ThroughLinks'

    link = tools.Delegate(ProviderLink, ctx)


class Publisher(Parser):

    name = ctx.name
    url = tools.OneOf(
        ctx.uri,
        tools.Join(ctx.sameAs)
    )

    class Extra:

        publisher = ctx


class Funder(Parser):

    community_identifier = tools.Try(ctx.sponsorIdentifier)
    name = ctx.sponsorName


class Award:

    # award will become name
    award = tools.Try(ctx.awardIdentifier)
    description = ctx.awardName
    url = tools.Try(ctx.awardIdentifier)


class ThroughAwards:

    award = tools.Delegate(Award, ctx)


class Institution(Parser):

    name = ctx


class Organization(Parser):

    name = ctx


class Association(Parser):
    pass


class Email(Parser):

    email = ctx


class PersonEmail(Parser):

    email = tools.Delegate(Email, ctx)


class Identifier(Parser):

    url = ctx


class ThroughIdentifiers(Parser):

    identifier = tools.Delegate(Identifier, ctx)


class Person(Parser):

    suffix = tools.ParseName(ctx.name).suffix
    family_name = tools.ParseName(ctx.name).last
    given_name = tools.ParseName(ctx.name).first
    additional_name = tools.ParseName(ctx.name).middle

    emails = tools.Map(
        tools.Delegate(PersonEmail),
        tools.Try(ctx.email)
    )
    affiliations = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Organization))),
        tools.Try(ctx.affiliation)
    )

    identifiers = tools.Map(
        tools.Delegate(ThroughIdentifiers),
        tools.Try(ctx.sameAs)
    )

    class Extra:

        givenName = tools.Try(ctx.givenName)

        familyName = tools.Try(ctx.familyName)

        additonalName = tools.Try(ctx.additionalName)

        name = tools.Try(ctx.name)


class Contributor(Parser):

    person = tools.Delegate(Person, ctx)
    cited_name = ctx.name
    order_cited = ctx('index')


class Tag(Parser):

    name = ctx


class ThroughTags(Parser):

    tag = tools.Delegate(Tag, ctx)


class Subject(Parser):

    name = ctx


class ThroughSubjects(Parser):

    subject = tools.Delegate(Subject, ctx)


class CreativeWork(Parser):

    ORGANIZATION_KEYWORDS = (
        THE_REGEX,
        'council',
        'center',
        'foundation'
    )
    INSTITUTION_KEYWORDS = (
        'school',
        'university',
        'institution',
        'college',
        'institute'
    )

    awards = tools.Map(
        tools.Delegate(ThroughAwards),
        tools.Try(ctx.sponsorships.award)
    )

    contributors = tools.Map(
        tools.Delegate(Contributor),
        tools.RunPython(
            'get_contributors',
            tools.Try(ctx.contributors),
            'contributor'
        )
    )

    date_updated = tools.ParseDate(tools.Try(ctx.providerUpdatedDateTime))

    description = tools.Try(ctx.description)

    funders = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Funder))),
        tools.Try(ctx.sponsorships.sponsor)
    )

    institutions = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Institution))),
        tools.RunPython(
            'get_contributors',
            tools.Try(ctx.contributors),
            'institution'
        )
    )

    # Note: this is only taking the first language in the case of multiple languages
    language = tools.ParseLanguage(
        tools.Try(ctx.languages[0]),
    )

    links = tools.Concat(
        tools.Map(
            tools.Delegate(ThroughLinks),
            tools.Try(ctx.uris.canonicalUri),
            tools.Try(ctx.uris.descriptorUris),
            tools.Try(ctx.uris.objectUris)
        ),
        tools.Map(
            tools.Delegate(ProviderThroughLinks),
            tools.Try(ctx.uris.providerUris),
        )
    )

    organizations = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Organization))),
        tools.RunPython(
            'get_contributors',
            tools.Try(ctx.contributors),
            'organization'
        )
    )

    # unsure how to tell difference between person and org
    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        tools.Try(ctx.publisher)
    )

    rights = tools.Join(tools.Try(ctx.licenses.uri))

    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Try(ctx.subjects)
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Try(ctx.tags),
        tools.Try(ctx.subjects)
    )

    title = ctx.title

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """

        freeToRead = tools.Try(ctx.freeToRead)

        languages = tools.Try(ctx.languages)

        licenses = tools.Try(ctx.licenses)

        otherProperties = tools.Try(ctx.otherProperties)

        publisher = tools.Try(ctx.publisher)

        subjects = tools.Try(ctx.subjects)

        sponsorships = tools.Try(ctx.sponsorships)

        tags = tools.Try(ctx.tags)

        uris = tools.Try(ctx.uris)

        version = tools.Try(ctx.version)

    def get_contributors(self, options, entity):
        """
        Returns list of organization, institutions, or contributors names based on entity type.
        """

        if entity == 'organization':
            organizations = [
                value for value in options if
                (
                    value['name'] and
                    not self.list_in_string(value['name'], self.INSTITUTION_KEYWORDS) and
                    self.list_in_string(value['name'], self.ORGANIZATION_KEYWORDS)
                )
            ]
            return organizations
        elif entity == 'institution':
            institutions = [
                value for value in options if
                (
                    value['name'] and
                    self.list_in_string(value['name'], self.INSTITUTION_KEYWORDS)
                )
            ]
            return institutions
        elif entity == 'contributor':
            people = [
                value for value in options if
                (
                    value['name'] and
                    not self.list_in_string(value['name'], self.INSTITUTION_KEYWORDS) and not
                    self.list_in_string(value['name'], self.ORGANIZATION_KEYWORDS)
                )
            ]
            return people
        else:
            return options

    def list_in_string(self, string, list_):
        for word in list_:
            if isinstance(word, str):
                if word in string.lower():
                    return True
            else:
                if word.search(string):
                    return True
        return False


class V1Normalizer(Normalizer):
    root_parser = CreativeWork
