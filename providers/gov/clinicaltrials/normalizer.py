from share.normalize import *


class Venue(Parser):
    name = Maybe(Maybe(ctx, 'facility'), 'name')


class ThroughVenues(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    pass


class Email(Parser):
    email = ctx


class PersonEmail(Parser):
    pass


class Entity(Parser):
    name = ctx


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = Maybe(ctx, 'first_name')
    family_name = Maybe(ctx, 'last_name')
    additional_name = Maybe(ctx, 'middle_name')
    emails = Map(Delegate(PersonEmail), Maybe(ctx, 'email'))
    affiliations = Map(Delegate(Affiliation.using(entity=Delegate(Entity))), Maybe(ctx, 'affiliation'))


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ''
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
