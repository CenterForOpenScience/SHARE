from share.normalize import *


class CreativeWork(Parser):
    # Dates in CrossRef metadata are often incomplete, see: https://github.com/CrossRef/rest-api-doc/blob/master/rest_api.md#notes-on-dates
    title = ctx.title[0]
    description = ctx.maybe('subtitle')
    doi = ctx.DOI
    contributors = ctx.author['*']
    tags = ctx.maybe('subject')['*']


class Contributor(Parser):
    # CrossRef does not return a complete cited name, but returns the given name and family name of the contributor
    person = ctx
    order_cited = ctx['index']


class Person(Parser):
    family_name = ctx.family
    given_name = ctx.given
    affiliations = ctx.affiliation['*']


class Organization(Parser):
    name = ctx.name
