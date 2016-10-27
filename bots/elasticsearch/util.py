import uuid

from django.apps import apps
from django.db import connection
from django.db import transaction

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
                    , 'language', creativework.language
                    , 'date_created', creativework.date_created
                    , 'date_modified', creativework.date_modified
                    , 'date_updated', creativework.date_updated
                    , 'date_published', creativework.date_published
                    , 'tags', COALESCE(tags, '{}')
                    , 'identifiers', COALESCE(identifiers, '{}')
                    , 'sources', sources
                    , 'subjects', COALESCE(subjects, '{}')
                    , 'related_agents', COALESCE(related_agents, '{}'))
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
                                                            ))) AS related_agents
                            FROM share_agentworkrelation AS agent_relation
                            JOIN share_agent AS agent ON agent_relation.agent_id = agent.id
                            LEFT JOIN LATERAL (
                                        SELECT array_agg(identifier.uri) AS identifiers
                                        FROM share_agentidentifier AS identifier
                                        WHERE identifier.agent_id = agent.id
                                        ) AS identifiers ON TRUE
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
                            SELECT array_agg(subject.name) AS subjects
                            FROM share_throughsubjects AS throughsubject
                            JOIN share_subject AS subject ON throughsubject.subject_id = subject.id
                            WHERE throughsubject.creative_work_id = creativework.id
                            ) AS subjects ON TRUE
                WHERE creativework.id IN %s
            ''', (tuple(pks), ))

            while True:
                data = c.fetchone()

                if not data:
                    return

                data = data[0]
                data['lists'] = {}

                for agent in data.pop('related_agents'):
                    populate_types(agent)
                    relation_model = apps.get_model(agent.pop('relation_type'))
                    parent_model = next(parent for parent in relation_model.mro() if not parent.mro()[2]._meta.proxy)
                    agent['relation'] = relation_model._meta.verbose_name
                    data.setdefault(str(parent_model._meta.verbose_name_plural), []).append(agent.get('cited_as') or agent['name'])
                    data['lists'].setdefault(str(parent_model._meta.verbose_name_plural), []).append(agent)

                populate_types(data)
                data['date'] = (data['date_published'] or data['date_updated'] or data['date_created'])

                yield data
