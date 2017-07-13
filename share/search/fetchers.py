import uuid
import bleach

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db import transaction

from project.settings import ALLOWED_TAGS

from share import models
from share.util import IDObfuscator


class Fetcher:

    MODEL = None
    QUERY = None

    @classmethod
    def fetcher_for(cls, model):
        for fetcher in cls.__subclasses__():
            if issubclass(model, fetcher.MODEL):
                return fetcher()
        raise ValueError('No fetcher exists for {!r}'.format(model))

    def __call__(self, pks):
        if self.QUERY is None:
            raise NotImplementedError

        pks = tuple(pks)
        if not pks:
            return []

        if connection.connection is None:
            connection.cursor()

        with transaction.atomic():
            with connection.connection.cursor(str(uuid.uuid4())) as c:
                c.execute(self.QUERY, self.query_parameters(pks))

                while True:
                    data = c.fetchone()

                    if not data:
                        return

                    yield self.post_process(data[0])

    def post_process(self, data):
        return self.populate_types(data)

    def populate_types(self, data):
        model = apps.get_model(data['type'])
        data['id'] = IDObfuscator.encode_id(data['id'], model)
        data['type'] = model._meta.verbose_name
        data['types'] = []
        for parent in model.__mro__:
            if not parent._meta.proxy:
                break
            data['types'].append(parent._meta.verbose_name)

        return data

    def query_parameters(self, pks):
        return {'ids': pks}


# For ease of use
fetcher_for = Fetcher.fetcher_for


class CreativeWorkFetcher(Fetcher):

    MODEL = models.AbstractCreativeWork
    QUERY = '''
        SELECT json_build_object(
            'id', creativework.id
            , 'type', creativework.type
            , 'title', creativework.title
            , 'description', creativework.description
            , 'is_deleted', creativework.is_deleted
            , 'language', creativework.language
            , 'date_created', creativework.date_created
            , 'date_modified', creativework.date_modified
            , 'date_updated', creativework.date_updated
            , 'date_published', creativework.date_published
            , 'registration_type', creativework.registration_type
            , 'withdrawn', creativework.withdrawn
            , 'justification', creativework.justification
            , 'tags', COALESCE(tags, '{}')
            , 'identifiers', COALESCE(identifiers, '{}')
            , 'sources', COALESCE(sources, '{}')
            , 'subjects', COALESCE(subjects, '{}')
            , 'subject_synonyms', COALESCE(subject_synonyms, '{}')
            , 'related_agents', COALESCE(related_agents, '{}')
            , 'retractions', COALESCE(retractions, '{}')
        )
        FROM share_creativework AS creativework
        LEFT JOIN LATERAL (
                    SELECT json_agg(json_strip_nulls(json_build_object(
                                                        'id', agent.id
                                                        , 'type', agent.type
                                                        , 'name', agent.name
                                                        , 'given_name', agent.given_name
                                                        , 'family_name', agent.family_name
                                                        , 'additional_name', agent.additional_name
                                                        , 'suffix', agent.suffix
                                                        , 'identifiers', COALESCE(identifiers, '{}')
                                                        , 'relation_type', agent_relation.type
                                                        , 'order_cited', agent_relation.order_cited
                                                        , 'cited_as', agent_relation.cited_as
                                                        , 'affiliations', COALESCE(affiliations, '[]'::json)
                                                        , 'awards', COALESCE(awards, '[]'::json)
                                                    ))) AS related_agents
                    FROM share_agentworkrelation AS agent_relation
                    JOIN share_agent AS agent ON agent_relation.agent_id = agent.id
                    LEFT JOIN LATERAL (
                                SELECT array_agg(identifier.uri) AS identifiers
                                FROM share_agentidentifier AS identifier
                                WHERE identifier.agent_id = agent.id
                                AND identifier.scheme != 'mailto'
                                LIMIT 51
                                ) AS identifiers ON TRUE
                    LEFT JOIN LATERAL (
                                SELECT json_agg(json_strip_nulls(json_build_object(
                                                                    'id', affiliated_agent.id
                                                                    , 'type', affiliated_agent.type
                                                                    , 'name', affiliated_agent.name
                                                                    , 'affiliation_type', affiliation.type
                                                                ))) AS affiliations
                                FROM share_agentrelation AS affiliation
                                JOIN share_agent AS affiliated_agent ON affiliation.related_id = affiliated_agent.id
                                WHERE affiliation.subject_id = agent.id AND affiliated_agent.type != 'share.person'
                                ) AS affiliations ON (agent.type = 'share.person')
                    LEFT JOIN LATERAL (
                                SELECT json_agg(json_strip_nulls(json_build_object(
                                                                    'id', award.id
                                                                    , 'type', 'share.award'
                                                                    , 'date', award.date
                                                                    , 'name', award.name
                                                                    , 'description', award.description
                                                                    , 'uri', award.uri
                                                                    , 'amount', award.award_amount
                                                                ))) AS awards
                                FROM share_throughawards AS throughaward
                                JOIN share_award AS award ON throughaward.award_id = award.id
                                WHERE throughaward.funder_id = agent_relation.id
                                ) AS awards ON agent_relation.type = 'share.funder'
                    WHERE agent_relation.creative_work_id = creativework.id
                    ) AS related_agents ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(identifier.uri) AS identifiers
                    FROM share_workidentifier AS identifier
                    WHERE identifier.creative_work_id = creativework.id
                    ) AS links ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(DISTINCT source.long_title) AS sources
                    FROM share_creativework_sources AS throughsources
                    JOIN share_shareuser AS shareuser ON throughsources.shareuser_id = shareuser.id
                    JOIN share_source AS source ON shareuser.id = source.user_id
                    WHERE throughsources.abstractcreativework_id = creativework.id
                    AND NOT source.is_deleted
                    ) AS sources ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(tag.name) AS tags
                    FROM share_throughtags AS throughtag
                    JOIN share_tag AS tag ON throughtag.tag_id = tag.id
                    WHERE throughtag.creative_work_id = creativework.id
                    ) AS tags ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(DISTINCT name) AS subjects
                    FROM (
                        SELECT concat_ws('/', CASE WHEN source.name = %(system_user)s THEN %(central_taxonomy)s ELSE source.long_title END, great_grand_parent.name, grand_parent.name, parent.name, child.name)
                        FROM share_subject AS child
                            LEFT JOIN share_subjecttaxonomy AS taxonomy ON child.taxonomy_id = taxonomy.id
                            LEFT JOIN share_source AS source ON taxonomy.source_id = source.id
                            LEFT JOIN share_subject AS parent ON child.parent_id = parent.id
                            LEFT JOIN share_subject AS grand_parent ON parent.parent_id = grand_parent.id
                            LEFT JOIN share_subject AS great_grand_parent ON grand_parent.parent_id = great_grand_parent.id
                        WHERE child.id IN (SELECT share_throughsubjects.subject_id
                                            FROM share_throughsubjects
                                            WHERE share_throughsubjects.creative_work_id = creativework.id
                                            AND NOT share_throughsubjects.is_deleted)
                              AND NOT child.is_deleted
                        ) AS x(name)
                    WHERE name IS NOT NULL
                    ) AS subjects ON TRUE
         LEFT JOIN LATERAL (
                   SELECT array_agg(DISTINCT name) AS subject_synonyms
                   FROM (
                       SELECT concat_ws('/', CASE WHEN source.name = %(system_user)s THEN %(central_taxonomy)s ELSE source.long_title END, great_grand_parent.name, grand_parent.name, parent.name, child.name)
                       FROM share_subject AS child
                           LEFT JOIN share_subjecttaxonomy AS taxonomy ON child.taxonomy_id = taxonomy.id
                           LEFT JOIN share_source AS source ON taxonomy.source_id = source.id
                           LEFT JOIN share_subject AS parent ON child.parent_id = parent.id
                           LEFT JOIN share_subject AS grand_parent ON parent.parent_id = grand_parent.id
                           LEFT JOIN share_subject AS great_grand_parent ON grand_parent.parent_id = great_grand_parent.id
                       WHERE child.id IN (SELECT share_subject.central_synonym_id
                                           FROM share_throughsubjects
                                           JOIN share_subject ON share_throughsubjects.subject_id = share_subject.id
                                           WHERE share_throughsubjects.creative_work_id = creativework.id
                                           AND NOT share_throughsubjects.is_deleted
                                           AND NOT share_subject.is_deleted)
                             AND NOT child.is_deleted
                       ) AS x(name)
                   WHERE name IS NOT NULL
                   ) AS subject_aliases ON TRUE
        LEFT JOIN LATERAL (
                    SELECT json_agg(json_strip_nulls(json_build_object(
                                                        'id', retraction.id
                                                        , 'type', retraction.type
                                                        , 'title', retraction.title
                                                        , 'description', retraction.description
                                                        , 'date_created', retraction.date_created
                                                        , 'date_modified', retraction.date_modified
                                                        , 'date_updated', retraction.date_updated
                                                        , 'date_published', retraction.date_published
                                                        , 'identifiers', COALESCE(identifiers, '{}')
                                                    ))) AS retractions
                    FROM share_workrelation AS work_relation
                    JOIN share_creativework AS retraction ON work_relation.subject_id = retraction.id
                    LEFT JOIN LATERAL (
                                SELECT array_agg(identifier.uri) AS identifiers
                                FROM share_workidentifier AS identifier
                                WHERE identifier.creative_work_id = retraction.id
                                ) AS identifiers ON TRUE
                    WHERE work_relation.related_id = creativework.id
                    AND work_relation.type = 'share.retracts'
                    AND NOT retraction.is_deleted
                    ) AS retractions ON TRUE
        WHERE creativework.id IN %(ids)s
        AND creativework.title != ''
        AND COALESCE(array_length(identifiers, 1), 0) < 51
    '''

    def query_parameters(self, pks):
        return {
            'ids': pks,
            'system_user': settings.APPLICATION_USERNAME,
            'central_taxonomy': settings.SUBJECTS_CENTRAL_TAXONOMY,
        }

    def post_process(self, data):
        data['lists'] = {}

        if data['title']:
            data['title'] = bleach.clean(data['title'], strip=True, tags=ALLOWED_TAGS)

        if data['description']:
            data['description'] = bleach.clean(data['description'], strip=True, tags=ALLOWED_TAGS)

        for agent in data.pop('related_agents'):
            self.populate_types(agent)

            for award in agent.get('awards', []):
                self.populate_types(award)

            for affiliation in agent.get('affiliations', []):
                self.populate_types(affiliation)
                affiliation['affiliation'] = apps.get_model(affiliation.pop('affiliation_type'))._meta.verbose_name

            relation_model = apps.get_model(agent.pop('relation_type'))
            parent_model = next(parent for parent in relation_model.__mro__ if not parent.__mro__[2]._meta.proxy)
            parent_name = str(parent_model._meta.verbose_name_plural)
            agent['relation'] = relation_model._meta.verbose_name
            data['lists'].setdefault(parent_name, []).append(agent)

            if relation_model == models.AgentWorkRelation:
                elastic_field = 'affiliations'
            else:
                elastic_field = parent_name
            data.setdefault(elastic_field, []).append(agent.get('cited_as') or agent['name'])

            if parent_model == models.Contributor:
                data.setdefault('affiliations', []).extend(a['name'] for a in agent['affiliations'])

        data['retracted'] = bool(data['retractions'])
        for retraction in data.pop('retractions'):
            self.populate_types(retraction)
            data['lists'].setdefault('retractions', []).append(retraction)

        data['date'] = (data['date_published'] or data['date_updated'] or data['date_created'])

        return super().post_process(data)


class AgentFetcher(Fetcher):

    MODEL = models.AbstractAgent
    QUERY = '''
        SELECT json_strip_nulls(json_build_object(
                                    'id', agent.id
                                    , 'type', agent.type
                                    , 'name', agent.name
                                    , 'family_name', agent.family_name
                                    , 'given_name', agent.given_name
                                    , 'additional_name', agent.additional_name
                                    , 'suffix', agent.suffix
                                    , 'location', agent.location
                                    , 'sources', COALESCE(sources, '{}')
                                    , 'identifiers', COALESCE(identifiers, '{}')
                                    , 'related_types', COALESCE(related_types, '{}')))
        FROM share_agent AS agent
        LEFT JOIN LATERAL (
                    SELECT array_agg(DISTINCT source.long_title) AS sources
                    FROM share_agent_sources AS throughsources
                    JOIN share_shareuser AS shareuser ON throughsources.shareuser_id = shareuser.id
                    JOIN share_source AS source ON shareuser.id = source.user_id
                    WHERE throughsources.abstractagent_id = agent.id
                    AND NOT source.is_deleted
                    ) AS sources ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(identifier.uri) AS identifiers
                    FROM share_agentidentifier AS identifier
                    WHERE identifier.agent_id = agent.id
                    AND identifier.scheme != 'mailto'
                    ) AS identifiers ON TRUE
        LEFT JOIN LATERAL (
                    SELECT array_agg(DISTINCT creative_work_relation.type) AS related_types
                    FROM share_agentworkrelation AS creative_work_relation
                    WHERE creative_work_relation.agent_id = agent.id
                    ) AS related_types ON TRUE
        WHERE agent.id in %(ids)s
    '''

    def post_process(self, data):
        data = super().post_process(data)

        for rtype in data.pop('related_types'):
            for relation_model in apps.get_model(rtype).__mro__:
                if not relation_model.__mro__[1]._meta.proxy:
                    break
                data['types'].append(relation_model._meta.verbose_name)
        data['types'] = list(set(data['types']))

        return data


class SubjectFetcher(Fetcher):

    MODEL = models.Subject

    def __call__(self, pks):
        for tag in models.Subject.objects.filter(id__in=pks):
            if not tag.name:
                continue
            yield {'id': IDObfuscator.encode(tag), 'type': 'subject', 'name': tag.name[:32000]}


class TagFetcher(Fetcher):

    MODEL = models.Tag

    def __call__(self, pks):
        for tag in models.Tag.objects.filter(id__in=pks):
            if not tag.name:
                continue
            yield {'id': IDObfuscator.encode(tag), 'type': 'tag', 'name': tag.name[:32000]}
