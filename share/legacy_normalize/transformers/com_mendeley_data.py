from share.legacy_normalize.transform.chain import *  # noqa
from share.legacy_normalize.transform.chain.utils import format_address


def format_mendeley_address(ctx):
    return format_address(
        address1=ctx['name'],
        city=ctx['city'],
        state_or_province=ctx['state'],
        country=ctx['country']
    )


RELATION_MAP = {
    'related_to': 'WorkRelation',
    'derived_from': 'IsDerivedFrom',
    'source_of': 'IsDerivedFrom',
    'compiles': 'Compiles',
    'compiled_by': 'Compiles',
    'cites': 'Cites',
    'cited_by': 'Cites',
}

INVERSE_RELATIONS = {
    'cited_by',
    'compiled_by',
    'derived_from'
}

RELATIONS = {
    'cites',
    'compiles',
    'source_of',
    'related_to',
}


def get_related_works(options, inverse):
    results = []
    for option in options:
        relation = option['rel']
        if inverse and relation in INVERSE_RELATIONS:
            results.append(option)
        elif not inverse and relation in RELATIONS:
            results.append(option)
    return results


def get_relation_type(relation_type):
    return RELATION_MAP.get(relation_type, 'WorkRelation')


def get_related_work_type(work_type):
    if work_type == 'other':
        return 'creativework'
    return work_type


class WorkIdentifier(Parser):
    uri = ctx


class Tag(Parser):
    name = ctx.label

    class Extra:
        id = ctx.id


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class RelatedWork(Parser):
    schema = RunPython(get_related_work_type, ctx.type)
    identifiers = Map(
        Delegate(WorkIdentifier),
        Try(
            IRI(ctx.href),
            exceptions=(InvalidIRI,)
        )
    )


class WorkRelation(Parser):
    schema = RunPython(get_relation_type, ctx.rel)
    related = Delegate(RelatedWork, ctx)


class InverseWorkRelation(Parser):
    schema = RunPython(get_relation_type, ctx.rel)
    subject = Delegate(RelatedWork, ctx)


class RelatedArticle(Parser):
    schema = 'Article'
    title = Try(ctx.title)
    identifiers = Map(
        Delegate(WorkIdentifier),
        Try(
            IRI(ctx.doi),
            exceptions=(InvalidIRI,)
        )
    )

    class Extra:
        journal = Try(ctx.journal)
        title = Try(ctx.title)
        doi = Try(ctx.doi)
        article_id = Try(ctx.id)


class UsesDataFrom(Parser):
    subject = Delegate(RelatedArticle, ctx)


class AgentIdentifier(Parser):
    uri = ctx


class AgentInstitution(Parser):
    schema = GuessAgentType(ctx.name, default='organization')

    name = Try(ctx.name)
    location = Try(RunPython(format_mendeley_address, ctx))
    identifiers = Map(
        Delegate(AgentIdentifier),
        Concat(
            Try(
                IRI(ctx.urls),
                exceptions=(InvalidIRI,)
            ),
            Try(
                IRI(ctx.profile_url),
                exceptions=(InvalidIRI,)
            )
        )
    )

    class Extra:
        name = Try(ctx.name)
        scival_id = Try(ctx.scival_id)
        instituion_id = Try(ctx.id)
        city = Try(ctx.city)
        state = Try(ctx.state)
        country = Try(ctx.country)
        parent_id = Try(ctx.parent_id)
        urls = Try(ctx.urls)
        profile_url = Try(ctx.profile_url)
        alt_names = Try(ctx.alt_names)


class AgentWorkRelation(Parser):
    agent = Delegate(AgentInstitution, ctx)


class IsAffiliatedWith(Parser):
    related = Delegate(AgentInstitution, ctx)


class Person(Parser):
    """
    {
      "id": "",
      "first_name": "",
      "last_name": "",
      "display_name": "",
      "link": "",
      "folder": "",
      "institution": "",
      "institution_details": {
        "scival_id": 0,
        "id": "",
        "name": "",
        "city": "",
        "state": "",
        "country": "",
        "parent_id": "",
        "urls": [
          ""
        ],
        "profile_url": "",
        "alt_names": [
          {
            "name": ""
          }
        ]
      },
      "location": {
        "id": "",
        "latitude": 0,
        "longitude": 0,
        "name": "",
        "city": "",
        "state": "",
        "country": ""
      },
      "created": "",
      "title": "",
      "web_user_id": 0,
      "scopus_author_ids": [
        ""
      ],
      "orcid_id": "",
    }
    """
    given_name = ctx.first_name
    family_name = ctx.last_name
    location = RunPython(format_mendeley_address, Try(ctx.full_profile.location))

    identifiers = Map(
        Delegate(AgentIdentifier),
        Concat(
            Try(
                IRI(ctx.full_profile.orcid_id),
                exceptions=(InvalidIRI,)
            ),
            Try(
                IRI(ctx.full_profile.link),
                exceptions=(InvalidIRI,)
            )
        )
    )

    related_agents = Concat(
        Map(Delegate(IsAffiliatedWith), Try(ctx.full_profile.institution_details)),
        Map(Delegate(IsAffiliatedWith), Try(ctx.institution)),
    )

    class Extra:
        profile_id = Try(ctx.profile_id)
        first_name = ctx.first_name
        last_name = ctx.last_name
        contribution = Try(ctx.contribution)
        full_profile = Try(ctx.full_profile)


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class Creator(Contributor):
    order_cited = ctx('index')
    cited_as = RunPython('full_name', ctx)

    def full_name(self, ctx):
        return '{} {}'.format(ctx['first_name'], ctx['last_name'])


class DataSet(Parser):
    """
    {
      "id": "",
      "doi": {
        "id": "",
        "status": ""
      },
      "name": "",
      "description": "",
      "contributors": [
        {
          "contribution": "",
          "institution": {
            "scival_id": 0,
            "id": "",
            "name": "",
            "city": "",
            "state": "",
            "country": "",
            "parent_id": "",
            "urls": [""],
            "profile_url": "",
            "alt_names": [{"name": ""}]
          },
          "profile_id": "",
          "first_name": "",
          "last_name": ""
        }
      ],
      "articles": [
        {
          "journal": {
            "url": "",
            "issn": "",
            "name": ""
          },
          "title": "",
          "doi": "",
          "id": ""
        }
      ],
      "institutions": [
        {
          "scival_id": 0,
          "id": "",
          "name": "",
          "city": "",
          "state": "",
          "country": "",
          "parent_id": "",
          "urls": [],
          "profile_url": "",
          "alt_names": [{"name": ""}]
        }
      ],
      "related_links": [
        {
          "type": "",
          "rel": "",
          "href": ""
        }
      ],
      "publish_date": "",
      "data_licence": {
        "description": "",
        "url": "",
        "full_name": "",
        "short_name": "",
        "id": ""
      },
      "embargo_date": ""
    }
    """

    schema = 'DataSet'
    title = Try(ctx.name)
    description = Try(ctx.description)

    # publish_date "reflects the published date of the most recent version of the dataset"
    date_published = ParseDate(Try(ctx.publish_date))
    date_updated = ParseDate(Try(ctx.publish_date))

    tags = Map(
        Delegate(ThroughTags),
        Try(ctx.categories)
    )
    subjects = Map(
        Delegate(ThroughSubjects),
        Subjects(Try(ctx.categories.label))
    )

    rights = Try(ctx.data_licence.description)
    free_to_read_type = Try(ctx.data_licence.url)
    free_to_read_date = ParseDate(Try(ctx.embargo_date))

    related_agents = Concat(
        Map(
            Delegate(Creator), RunPython('filter_contributors', Try(ctx.contributors), 'creator')
        ),
        Map(
            Delegate(Contributor), RunPython('filter_contributors', Try(ctx.contributors), 'contributor')
        ),
        Map(
            Delegate(AgentWorkRelation), Try(ctx.institutions)
        )
    )

    related_works = Concat(
        Map(
            Delegate(UsesDataFrom),
            Try(ctx.articles)  # Journal articles associated with the dataset
        ),
        Map(
            Delegate(WorkRelation),
            RunPython(
                get_related_works,
                Try(ctx.related_links),
                False
            )
        ),
        Map(
            Delegate(InverseWorkRelation),
            RunPython(
                get_related_works,
                Try(ctx.related_links),
                True
            )
        )
    )

    identifiers = Map(
        Delegate(WorkIdentifier),
        Concat(
            RunPython(lambda mendeley_id: 'https://data.mendeley.com/datasets/{}'.format(mendeley_id) if mendeley_id else None, Try(ctx.id)),
            Try(
                IRI(ctx.doi.id),
                exceptions=(InvalidIRI,)
            )
        )
    )

    def filter_contributors(self, contributor_list, contributor_type):
        filtered = []
        for contributor in contributor_list:
            try:
                if not contributor['contribution'] and contributor_type == 'creator':
                    filtered.append(contributor)
                elif contributor['contribution'] and contributor_type == 'contributor':
                    filtered.append(contributor)
            except KeyError:
                if contributor_type == 'creator':
                    filtered.append(contributor)
        return filtered

    class Extra:
        """ Documentation:
        http://dev.mendeley.com/methods/#datasets
        http://dev.mendeley.com/methods/#profile-attributes
        """
        mendeley_id = Try(ctx.id)
        doi = Try(ctx.doi)
        name = Try(ctx.name)
        description = Try(ctx.description)
        version = Try(ctx.version)
        contributors = Try(ctx.contributors)
        versions = Try(ctx.versions)
        files = Try(ctx.files)
        articles = Try(ctx.articles)
        categories = Try(ctx.categories)
        institutions = Try(ctx.institutions)
        metrics = Try(ctx.metrics)
        available = Try(ctx.available)
        method = Try(ctx.method)
        related_links = Try(ctx.related_links)
        publish_date = ctx.publish_date
        data_licence = Try(ctx.data_licence)
        owner_id = Try(ctx.owner_id)
        embargo_date = Try(ctx.embargo_date)


class MendeleyTransformer(ChainTransformer):
    VERSION = 1
    root_parser = DataSet
