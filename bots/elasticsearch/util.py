from django.db import connection


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


def fetch_person(pk):
    with connection.cursor() as c:
        c.execute('''
            SELECT
            share_person.suffix
            , share_person.given_name
            , share_person.family_name
            , share_person.additional_name
            , share_identifier.url
            , share_identifier.base_url
            , share_entity.id
            , share_entity.name
            , share_entity.type
            , share_entity.url
            , share_entity.location
            , share_shareuser.long_title
            FROM share_person
            left JOIN share_throughidentifiers ON share_person.id = share_throughidentifiers.person_id
            left JOIN share_identifier ON share_throughidentifiers.identifier_id = share_identifier.id
            left JOIN share_affiliation ON share_person.id = share_affiliation.person_id
            left JOIN share_entity ON share_affiliation.entity_id = share_entity.id
            left JOIN share_person_sources ON share_person.id = share_person_sources.person_id
            left JOIN share_shareuser ON share_shareuser.id = share_person_sources.shareuser_id
            WHERE share_person.id = %s
        ''', (pk, ))

        data = c.fetchall()

    (
        suffix, given_name, family_name, additional_name,
        urls, base_urls,
        entity_ids, entity_types, entity_names, entity_urls, entity_locations,
        sources
    ) = zip(*data)

    return {
        'id': pk,
        'type': 'person',
        'name': ' '.join(x for x in [given_name[0], family_name[0], additional_name[0], suffix[0]] if x),
        'suffix': suffix[0],
        'given_name': given_name[0],
        'family_name': family_name[0],
        'additional_name': additional_name[0],
        'identifiers': [
            link for link in
            unique_by('url', sql_to_dict(('url', 'base_url'), (urls, base_urls)))
            if link['url']
        ],
        'affiliations': [
            entity for entity in
            unique_by('id', sql_to_dict(
                ('id', 'type', 'name', 'url', 'location'),
                (entity_ids, entity_types, entity_names, entity_urls, entity_locations)
            )) if entity['id']
        ],
        'sources': sorted(set(sources)),
    }


def fetch_abstractcreativework(pk):
    with connection.cursor() as c:
        c.execute('''
            SELECT
            share_abstractcreativework.id
            , share_abstractcreativework.type
            , share_abstractcreativework.title
            , share_abstractcreativework.description
            , share_abstractcreativework.language
            , share_abstractcreativework.date_created
            , share_abstractcreativework.date_modified
            , share_abstractcreativework.date_updated
            , share_abstractcreativework.date_published
            , share_tag.name
            , share_subject.name
            , share_entity.id
            , share_entity.type
            , share_entity.name
            , share_entity.url
            , share_entity.location
            , share_shareuser.long_title
            , share_link.url
            , share_link.type
            , share_venue.name
            , share_award.award
            , share_contributor.person_id
            , share_contributor.cited_name
            , share_contributor.order_cited
            , share_contributor.bibliographic
            FROM share_abstractcreativework
            LEFT JOIN share_contributor ON share_abstractcreativework.id = share_contributor.creative_work_id
            LEFT JOIN share_throughtags ON share_abstractcreativework.id = share_throughtags.creative_work_id
            LEFT JOIN share_tag ON share_throughtags.tag_id = share_tag.id
            LEFT JOIN share_throughsubjects ON share_abstractcreativework.id = share_throughsubjects.creative_work_id
            LEFT JOIN share_subject ON share_throughsubjects.subject_id = share_subject.id
            LEFT JOIN share_association ON share_association.creative_work_id = share_abstractcreativework.id
            LEFT JOIN share_entity ON share_association.entity_id = share_entity.id
            LEFT JOIN share_abstractcreativework_sources ON share_abstractcreativework.id = share_abstractcreativework_sources.abstractcreativework_id
            LEFT JOIN share_shareuser ON share_abstractcreativework_sources.shareuser_id = share_shareuser.id
            LEFT JOIN share_throughlinks ON share_abstractcreativework.id = share_throughlinks.creative_work_id
            LEFT JOIN share_link ON share_throughlinks.link_id = share_link.id
            LEFT JOIN share_throughawards ON share_abstractcreativework.id = share_throughawards.creative_work_id
            LEFT JOIN share_award ON share_throughawards.award_id = share_award.id
            LEFT JOIN share_throughvenues ON share_abstractcreativework.id = share_throughvenues.creative_work_id
            LEFT JOIN share_venue ON share_throughvenues.venue_id = share_venue.id
            WHERE share_abstractcreativework.id = %s
        ''', (pk, ))

        data = c.fetchall()

        (
            id, type, title, description, language, date_created, date_modified, date_updated, date_published,
            tags,
            subjects,
            entity_ids, entity_types, entity_names, entity_urls, entity_locations,
            sources,
            link_urls, link_types,
            venue_names,
            award_names,
            person_ids, name_cited, order_cited, bibliographic
        ) = zip(*data)

    contributors = [
        {**contrib, **fetch_person(contrib['person_id'])}
        for contrib in
        sorted(unique_by('person_id', sql_to_dict(
            ('person_id', 'name_cited', 'order_cited', 'bibliographic'),
            (person_ids, name_cited, order_cited, bibliographic),
        )), key=lambda x: x['order_cited'])
        if contrib['person_id']
    ]

    associations = {
        'funders': {},
        'publishers': {},
        'institutions': {},
        'organizations': {}
    }
    for entity in sql_to_dict(('id', 'type', 'name', 'url', 'location'), (entity_ids, entity_types, entity_names, entity_urls, entity_locations)):
        if not entity['id']:
            continue
        entity['type'] = entity['type'].split('.')[-1]
        associations.setdefault(entity['type'] + 's', {})[entity['id']] = entity
    associations = {k: list(v.values()) for k, v in associations.items()}

    return {
        'id': pk,
        'type': type[0].split('.')[-1],
        'title': title[0],
        'description': description[0],
        'language': language[0],
        'date': (date_published[0] or date_updated[0] or date_created[0]).isoformat(),
        'date_created': date_created[0].isoformat(),
        'date_modified': date_modified[0].isoformat(),
        'date_updated': date_updated[0].isoformat() if date_updated[0] else None,
        'date_published': date_published[0].isoformat() if date_published[0] else None,
        'tags': sorted(filter(None, set(tags))),
        'subjects': sorted(filter(None, set(subjects))),
        'awards': sorted(filter(None, set(venue_names))),
        'venues': sorted(filter(None, set(award_names))),
        'sources': sorted(filter(None, set(sources))),
        'funders': [x['name'] for x in associations['funders']],
        'publishers': [x['name'] for x in associations['publishers']],
        'institutions': [x['name'] for x in associations['institutions']],
        'organizations': [x['name'] for x in associations['funders']],
        'contributors': [x['name'] for x in contributors],

        'lists': {
            **associations,
            'contributors': contributors,
            'links': unique_by('url', sql_to_dict(('url', 'type'), (link_urls, link_types))),
        },
    }
