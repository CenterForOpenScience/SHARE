import uuid
import itertools

from django.db import connection
from django.db import transaction


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


def fetch_person(pks):
    if connection.connection is None:
        connection.cursor()

    with transaction.atomic():
        with connection.connection.cursor(str(uuid.uuid4())) as c:
            c.execute('''
                SELECT json_build_object(
                    'id', person.id
                    , 'type', 'person'
                    , 'given_name', person.given_name
                    , 'family_name', person.family_name
                    , 'additional_name', person.additional_name
                    , 'sources', sources
                    , 'identifiers', COALESCE(identifiers, '[]' :: JSON)
                )
                FROM share_person AS person
                LEFT JOIN LATERAL (
                            SELECT json_agg(json_build_object('id', identifier.id, 'url', identifier.url)) AS identifiers
                            FROM share_personidentifier AS throughidentifier
                            JOIN share_identifier AS identifier ON throughidentifier.identifier_id = identifier.id
                            WHERE throughidentifier.person_id = person.id) AS identifiers ON TRUE
                LEFT JOIN LATERAL (
                            SELECT json_agg(
                                json_build_object('id', entity.id, 'type', entity.type, 'name', entity.name, 'url', entity.url,
                                                'location', entity.location))
                            FROM share_affiliation AS affiliation
                            JOIN share_entity AS entity ON affiliation.entity_id = entity.id
                            WHERE affiliation.person_id = person.id

                            ) AS affiliations ON TRUE
                LEFT JOIN LATERAL (
                            SELECT array_agg(source.long_title) AS sources
                            FROM share_person_sources AS throughsources
                            JOIN share_shareuser AS source ON throughsources.shareuser_id = source.id
                            WHERE throughsources.person_id = person.id
                            ) AS sources ON TRUE
                WHERE person.id in %s
            ''', (tuple(pks), ))

            while True:
                data = c.fetchone()

                if not data:
                    return

                yield data[0]


def fetch_abstractcreativework(pks):
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
                , 'associations', COALESCE(associations, '{}')
                , 'contributors', COALESCE(contributors, '{}'))
                FROM share_abstractcreativework AS creativework
                LEFT JOIN LATERAL(
                    SELECT json_agg(json_build_object('id', entity.id, 'type', entity.type, 'name', entity.name)) as associations
                    FROM share_association AS association
                    JOIN share_entity AS entity ON association.entity_id = entity.id
                    WHERE association.creative_work_id = creativework.id
                ) AS associations ON true
                LEFT JOIN LATERAL (
                    SELECT array_agg(identifier.url) as identifiers
                    FROM share_workidentifier AS throughidentifier
                    JOIN share_identifier AS identifier ON throughidentifier.identifier_id = identifier.id
                    WHERE throughidentifier.creative_work_id = creativework.id
                ) AS links ON true
                LEFT JOIN LATERAL (
                    SELECT array_agg(source.long_title) AS sources
                    FROM share_abstractcreativework_sources AS throughsources
                    JOIN share_shareuser AS source ON throughsources.shareuser_id = source.id
                    WHERE throughsources.abstractcreativework_id = creativework.id
                ) AS sources ON true
                LEFT JOIN LATERAL (
                    SELECT array_agg(tag.name) AS tags
                    FROM share_throughtags AS throughtag
                    JOIN share_tag AS tag ON throughtag.tag_id = tag.id
                    WHERE throughtag.creative_work_id = creativework.id
                ) AS tags ON true
                LEFT JOIN LATERAL (
                    SELECT array_agg(subject.name) AS subjects
                    FROM share_throughsubjects AS throughsubject
                    JOIN share_subject AS subject ON throughsubject.subject_id = subject.id
                    WHERE throughsubject.creative_work_id = creativework.id
                ) AS subjects ON true
                LEFT JOIN LATERAL (
                    SELECT json_agg(json_build_object(
                        'id', person.id
                        , 'order_cited', contributor.order_cited
                        , 'bibliographic', contributor.bibliographic
                        , 'cited_name', contributor.cited_name
                        , 'given_name', person.given_name
                        , 'family_name', person.family_name
                        , 'additional_name', person.additional_name
                        , 'suffix', person.suffix
                        , 'identifiers', COALESCE(identifiers, '{}')
                    )) AS contributors
                    FROM share_contributor AS contributor
                    JOIN share_person AS person ON contributor.person_id = person.id
                    LEFT JOIN LATERAL (
                        SELECT array_agg(identifier.url) AS identifiers
                        FROM share_personidentifier AS throughidentifier
                        JOIN share_identifier as identifier ON throughidentifier.identifier_id = identifier.id
                        WHERE throughidentifier.person_id = person.id
                    ) AS identifiers ON true
                    WHERE contributor.creative_work_id = creativework.id
                ) AS contributors ON true
                WHERE creativework.id IN %s
            ''', (tuple(pks), ))

            while True:
                data = c.fetchone()

                if not data:
                    return

                data = data[0]

                associations = {
                    k + 's': [{**e, 'type': k} for e in v]
                    for k, v in
                    itertools.groupby(data.pop('associations'), lambda x: x['type'].rpartition('.')[-1])
                }

                data['type'] = data['type'].rpartition('.')[-1]
                data['date'] = (data['date_published'] or data['date_updated'] or data['date_created'])

                data['lists'] = {
                    **associations,
                    'identifiers': data.pop('identifiers', []),
                    'contributors': sorted(data.pop('contributors', []), key=lambda x: x['order_cited']),
                }

                data['contributors'] = [
                    ' '.join(x for x in (p['given_name'], p['family_name'], p['additional_name'], p['suffix']) if x)
                    for p in data['lists']['contributors']
                ]

                yield {**data, **{k: [e['name'] for e in v] for k, v in associations.items()}}
