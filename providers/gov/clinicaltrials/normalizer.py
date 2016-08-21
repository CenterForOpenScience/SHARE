from share.normalize import *


class Venue(Parser):
    name = Maybe(Maybe(ctx, 'facility'), 'name')


class ThroughVenues(Parser):
    venue = Delegate(Venue, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Email(Parser):
    email = ctx


class PersonEmail(Parser):
    email = Delegate(Email, ctx)


class Organization(Parser):
    name = ctx


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = Maybe(ctx, 'first_name')
    family_name = Maybe(ctx, 'last_name')
    additional_name = Maybe(ctx, 'middle_name')
    emails = Map(Delegate(PersonEmail), Maybe(ctx, 'email'))
    affiliations = Map(Delegate(Affiliation.using(entity=Delegate(Organization))), Maybe(ctx, 'affiliation'))


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = Join(Concat(Maybe(ctx, 'first_name'), Maybe(ctx, 'last_name')), joiner=' ')
    person = Delegate(Person, ctx)


class CreativeWork(Parser):
    title = Maybe(ctx.clinical_study, 'official_title')
    description = Maybe(ctx.clinical_study, 'brief_summary')['textblock']
    contributors = Map(
        Delegate(Contributor),
        Maybe(ctx.clinical_study, 'overall_official'),
        Maybe(ctx.clinical_study, 'overall_contact'),
        Maybe(ctx.clinical_study, 'overall_contact_backup')
    )
    tags = Map(Delegate(ThroughTags), Maybe(ctx.clinical_study, 'keyword'))
    venues = Map(Delegate(ThroughVenues), Maybe(ctx.clinical_study, 'location'))
