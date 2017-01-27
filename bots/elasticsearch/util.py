import uuid
import bleach

from django.apps import apps
from django.db import connection
from django.db import transaction

from project.settings import ALLOWED_TAGS

from share import models
from share.util import IDObfuscator


def sql_to_dict(keys, values):
    ret = []
    for i in range(len(values[0])):
        ret.append({key: values[j][i] for j, key in enumerate(keys)})
    return ret


def unique_by(key, values):
    ret = {}
    for val in values:
        ret[val[key]] = val
    return list(ret.values())


def populate_types(data):
    model = apps.get_model(data['type'])
    data['id'] = IDObfuscator.encode_id(data['id'], model)
    data['type'] = model._meta.verbose_name
    data['types'] = []
    for parent in model.mro():
        if not parent._meta.proxy:
            break
        data['types'].append(parent._meta.verbose_name)

    return data


def fetch_agent(pks):
    if connection.connection is None:
        connection.cursor()

    with transaction.atomic():
        with connection.connection.cursor(str(uuid.uuid4())) as c:
            c.execute('''
                SELECT json_strip_nulls(json_build_object(
                                            'id', agent.id
                                            , 'type', agent.type
                                            , 'name', agent.name
                                            , 'family_name', agent.family_name
                                            , 'given_name', agent.given_name
                                            , 'additional_name', agent.additional_name
                                            , 'suffix', agent.suffix
                                            , 'location', agent.location
                                            , 'same_as', agent.same_as_id
                                            , 'sources', COALESCE(sources, '{}')
                                            , 'identifiers', COALESCE(identifiers, '{}')
                                            , 'related_types', COALESCE(related_types, '{}')))
                FROM share_agent AS agent
                LEFT JOIN LATERAL (
                            SELECT array_agg(source.long_title) AS sources
                            FROM share_agent_sources AS throughsources
                            JOIN share_shareuser AS source ON throughsources.shareuser_id = source.id
                            WHERE throughsources.abstractagent_id = agent.id
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
                WHERE agent.id in %s
            ''', (tuple(pks), ))

            while True:
                data = c.fetchone()

                if not data:
                    return

                data = data[0]
                populate_types(data)

                for rtype in data.pop('related_types'):
                    for relation_model in apps.get_model(rtype).mro():
                        if not relation_model.mro()[1]._meta.proxy:
                            break
                        data['types'].append(relation_model._meta.verbose_name)
                data['types'] = list(set(data['types']))

                yield data


def fetch_creativework(pks):
    if connection.connection is None:
        connection.cursor()

    with transaction.atomic():
        with connection.connection.cursor(str(uuid.uuid4())) as c:
            c.execute('''
                SELECT json_build_object(
                    'id', creativework.id
                    , 'type', creativework.type
                    , 'title', creativework.title
                    , 'description', creativework.description
                    , 'is_deleted', creativework.is_deleted
                    , 'same_as', creativework.same_as_id
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
                    , 'sources', sources
                    , 'subjects', COALESCE(subjects, '{}')
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
                            SELECT array_agg(source.long_title) AS sources
                            FROM share_creativework_sources AS throughsources
                            JOIN share_shareuser AS source ON throughsources.shareuser_id = source.id
                            WHERE throughsources.abstractcreativework_id = creativework.id
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
                                SELECT unnest(ARRAY [child.name, parent.name, grand_parent.name, great_grand_parent.name])
                                FROM share_subject AS child
                                    LEFT JOIN share_subject AS parent ON child.parent_id = parent.id
                                    LEFT JOIN share_subject AS grand_parent ON parent.parent_id = grand_parent.id
                                    LEFT JOIN share_subject AS great_grand_parent ON grand_parent.parent_id = great_grand_parent.id
                                WHERE child.id IN (SELECT share_throughsubjects.subject_id
                                                    FROM share_throughsubjects
                                                    WHERE share_throughsubjects.creative_work_id = creativework.id)
                                ) AS x(name)
                            WHERE name IS NOT NULL
                            ) AS subjects ON TRUE
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
                WHERE creativework.id IN %s
                AND creativework.title != ''
            ''', (tuple(pks), ))

            while True:
                data = c.fetchone()

                if not data:
                    return

                data = data[0]
                data['lists'] = {}

                if data['description']:
                    data['description'] = bleach.clean(data['description'], strip=True, tags=ALLOWED_TAGS)
                if data['title']:
                    data['title'] = bleach.clean(data['title'], strip=True, tags=ALLOWED_TAGS)

                for agent in data.pop('related_agents'):
                    populate_types(agent)

                    for award in agent.get('awards', []):
                        populate_types(award)

                    for affiliation in agent.get('affiliations', []):
                        populate_types(affiliation)
                        affiliation['affiliation'] = apps.get_model(affiliation.pop('affiliation_type'))._meta.verbose_name

                    relation_model = apps.get_model(agent.pop('relation_type'))
                    parent_model = next(parent for parent in relation_model.mro() if not parent.mro()[2]._meta.proxy)
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
                    populate_types(retraction)
                    data['lists'].setdefault('retractions', []).append(retraction)

                populate_types(data)
                data['date'] = (data['date_published'] or data['date_updated'] or data['date_created'])

                yield data
