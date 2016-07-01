from share.normalize import *


class CreativeWork(Parser):
    title = ctx.clinical_study.maybe('official_title')
    description = ctx.clinical_study.maybe('brief_summary')('textblock')
    contributors = ctx.clinical_study.maybe('overall_contact')['*']
    tags = ctx.clinical_study.maybe('keyword')['*']
    venues = ctx.clinical_study.maybe('location')['*']


class Contributor(Parser):
    order_cited = ctx['index']
    cited_name = ''
    person = ctx


class Person(Parser):
    given_name = ctx.maybe('first_name')
    family_name = ctx.maybe('last_name')
    additional_name = ctx.maybe('middle_name')
    emails = ctx.maybe('email')['*']


class PersonEmail(Parser):
    email = ctx


class Email(Parser):
    email = ctx


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = ctx


class Venue(Parser):
    name = ctx.maybe('facility').maybe('name')


class ThroughVenues(Parser):
    venue = ctx
