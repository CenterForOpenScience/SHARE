import sys
import bleach
import logging
import time

# from stevedore.extension import ExtensionManager

from django.apps import apps
from django.conf import settings
from django.db import connection

from project.settings import ALLOWED_TAGS

from share import models
from share.util import IDObfuscator


logger = logging.getLogger(__name__)


class Fetcher:
    """
    All Queries must return 2 columns, the pk of the result and the _source that will be sent to elasticsearch,
    formatted/named as (id, _source). To filter your selections by the ids given to the fetcher use:
        `WHERE table_name.id IN (SELECT id FROM pks)`
    """

    QUERY = None
    QUERY_TEMPLATE = '''
    WITH pks AS (SELECT * FROM UNNEST(%(ids)s::int[]) WITH ORDINALITY t(id, ord)),
         results AS ({0})
    SELECT _source FROM results
    RIGHT OUTER JOIN pks ON pks.id = results.id
    ORDER BY pks.ord;
    '''

    @classmethod
    def fetcher_for(cls, model, overrides=None):
        if not model._meta.concrete_model.__subclasses__():
            model_name = model._meta.model_name.lower()
        else:
            model_name = model._meta.concrete_model.__subclasses__()[0]._meta.model_name.lower()
        try:
            fetcher_path = (overrides or {}).get(model_name) or settings.ELASTICSEARCH['DEFAULT_FETCHERS'][model_name]
        except KeyError:
            raise ValueError('No fetcher exists for {!r}'.format(model))
        module, _, name = fetcher_path.rpartition('.')
        __import__(module)
        return getattr(sys.modules[module], name)()

    def __call__(self, pks):
        if self.QUERY is None:
            raise NotImplementedError

        pks = tuple(pks)
        if not pks:
            return []

        if connection.connection is None:
            connection.cursor()

        with connection.connection.cursor() as c:
            start = time.time() * 1000
            logger.debug('Fetching %d rows using %r', len(pks), self)
            c.execute(self.QUERY_TEMPLATE.format(self.QUERY), self.query_parameters(pks))
            logger.debug('Main query execution of %r took %dms', self, time.time() * 1000 - start)

            while True:
                data = c.fetchone()

                if not data:
                    logger.debug('Entire fetching processes of %r took %dms', self, time.time() * 1000 - start)
                    return

                if data[0] is None:
                    yield None
                else:
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
        return {'ids': '{' + ','.join(str(pk) for pk in pks) + '}'}


# For ease of use
fetcher_for = Fetcher.fetcher_for


class CreativeWorkFetcher(Fetcher):
    SUBJECT_DELIMITER = '|'
    RETRACTION_RELATION = 'share.retracts'
    PARENT_RELATION = 'share.ispartof'
    WORK_ANCESTORS_DEPTH = 3
    MAX_IDENTIFIERS = 50

    QUERY_TEMPLATE = '''
    WITH pks AS (SELECT * FROM UNNEST(%(ids)s::int[]) WITH ORDINALITY t(id, ord)),
         {0}
    SELECT _source FROM results
    RIGHT OUTER JOIN pks ON pks.id = results.id
    ORDER BY pks.ord;
    '''

    QUERY = '''
    all_tags AS (
        SELECT
            creative_work_id AS creativework_id,
            array_agg(share_tag.name) AS tags
        FROM share_tag
            JOIN share_throughtags ON share_tag.id = share_throughtags.tag_id
        WHERE share_throughtags.creative_work_id IN (SELECT id FROM pks)
        GROUP BY creative_work_id
    ),
    all_sources AS (
        SELECT
             abstractcreativework_id AS creativework_id,
             array_agg(DISTINCT share_source.long_title) AS sources
        FROM share_creativework_sources
            JOIN share_shareuser ON share_creativework_sources.shareuser_id = share_shareuser.id
            JOIN share_source ON share_shareuser.id = share_source.user_id
        WHERE share_creativework_sources.abstractcreativework_id IN (SELECT id FROM pks)
        AND NOT share_source.is_deleted
        GROUP BY abstractcreativework_id
    ),
    all_related_agents AS (
        SELECT
            agent_relation.creative_work_id AS creativework_id,
            json_agg(json_strip_nulls(json_build_object(
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
            SELECT
                array_agg(identifier.uri) AS identifiers
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

        WHERE agent_relation.creative_work_id IN (SELECT id FROM pks)
        GROUP BY agent_relation.creative_work_id
    ),
    results AS (
        SELECT creativework.id, json_build_object(
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
            , 'subjects', COALESCE(subjects.original, '{}')
            , 'subject_synonyms', COALESCE(subjects.synonyms, '{}')
            , 'related_agents', COALESCE(related_agents, '{}')
            , 'retractions', COALESCE(retractions, '{}')
            , 'lineage', COALESCE(lineage, '{}')
        ) AS _source
        FROM share_creativework AS creativework

        LEFT JOIN LATERAL (
            SELECT sources FROM all_sources WHERE creativework_id = creativework.id
        ) AS sources ON TRUE

        LEFT JOIN LATERAL (
            SELECT tags FROM all_tags WHERE creativework_id = creativework.id
        ) AS tags ON TRUE

        LEFT JOIN LATERAL (
            SELECT related_agents FROM all_related_agents WHERE creativework_id = creativework.id
        ) AS related_agents ON TRUE

        LEFT JOIN LATERAL (
            SELECT array_agg(identifier.uri) AS identifiers
            FROM share_workidentifier AS identifier
            WHERE identifier.creative_work_id = creativework.id
        ) AS identifiers ON TRUE

        LEFT JOIN LATERAL (
            WITH RECURSIVE subject_names(synonym, taxonomy, parent_id, path) AS (
                SELECT
                    FALSE,
                    CASE WHEN source.name = %(system_user)s THEN %(central_taxonomy)s ELSE source.long_title END,
                    parent_id,
                    share_subject.name
                FROM share_throughsubjects
                    JOIN share_subject ON share_subject.id = share_throughsubjects.subject_id
                    JOIN share_subjecttaxonomy AS taxonomy ON share_subject.taxonomy_id = taxonomy.id
                    JOIN share_source AS source ON taxonomy.source_id = source.id
                WHERE share_throughsubjects.creative_work_id = creativework.id
                    AND NOT share_throughsubjects.is_deleted
                UNION ALL
                    SELECT
                        TRUE, %(central_taxonomy)s, central.parent_id, central.name
                    FROM share_throughsubjects
                        JOIN share_subject ON share_subject.id = share_throughsubjects.subject_id
                        JOIN share_subject AS central ON central.id = share_subject.central_synonym_id
                    WHERE share_throughsubjects.creative_work_id = creativework.id
                        AND NOT share_throughsubjects.is_deleted

                UNION ALL
                    SELECT
                        synonym,
                        child.taxonomy,
                        parent.parent_id,
                        concat_ws(%(subject_delimiter)s, parent.name, path)
                    FROM subject_names AS child
                        INNER JOIN share_subject AS parent ON child.parent_id = parent.id
            ) SELECT
                (
                    SELECT array_agg(DISTINCT concat_ws(%(subject_delimiter)s, taxonomy, path))
                    FROM subject_names
                    WHERE NOT synonym AND parent_id IS NULL
                ) AS original,
                (
                    SELECT array_agg(DISTINCT concat_ws(%(subject_delimiter)s, taxonomy, path))
                    FROM subject_names
                    WHERE synonym AND parent_id IS NULL
                ) AS synonyms
        ) AS subjects ON TRUE

        LEFT JOIN LATERAL (
            WITH RECURSIVE ancestors(depth, id, type, title, identifiers) AS (
                VALUES (0, creativework.id, NULL, NULL, NULL::text[])
                UNION (
                    SELECT
                        child.depth + 1, parent.id, parent.type, parent.title, COALESCE(parent_identifiers.identifiers, '{}')
                    FROM ancestors AS child
                        JOIN share_workrelation AS work_relation ON child.id = work_relation.subject_id
                        JOIN share_creativework AS parent ON work_relation.related_id = parent.id
                        LEFT JOIN LATERAL (
                            SELECT array_agg(identifier.uri) AS identifiers
                            FROM share_workidentifier AS identifier
                            WHERE identifier.creative_work_id = parent.id
                        ) AS parent_identifiers ON TRUE
                    WHERE work_relation.type = %(parent_relation)s
                        AND child.depth < %(work_ancestors_depth)s
                        AND NOT parent.is_deleted
                    LIMIT 1
                )
            )
            SELECT json_agg(json_strip_nulls(json_build_object(
                    'id', id
                    , 'type', type
                    , 'title', title
                    , 'identifiers', identifiers
                ))) AS lineage
            FROM ancestors
            WHERE depth > 0
        ) AS lineage ON TRUE

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
                AND work_relation.type = %(retraction_relation)s
                AND NOT retraction.is_deleted
        ) AS retractions ON TRUE

        WHERE creativework.id IN (SELECT id FROM pks)
        AND creativework.title != ''
        AND (
            SELECT COUNT(*) FROM share_workidentifier
            WHERE share_workidentifier.creative_work_id = creativework.id
            LIMIT %(max_identifiers)s + 1
        ) <= %(max_identifiers)s
    )
    '''

    def query_parameters(self, pks):
        return {
            **super().query_parameters(pks),
            'central_taxonomy': settings.SUBJECTS_CENTRAL_TAXONOMY,
            'subject_delimiter': self.SUBJECT_DELIMITER,
            'system_user': settings.APPLICATION_USERNAME,
            'retraction_relation': self.RETRACTION_RELATION,
            'parent_relation': self.PARENT_RELATION,
            'work_ancestors_depth': self.WORK_ANCESTORS_DEPTH,
            'max_identifiers': self.MAX_IDENTIFIERS,
        }

    def post_process(self, data):
        data['lists'] = {}

        if data['title']:
            data['title'] = bleach.clean(data['title'], strip=True, tags=ALLOWED_TAGS)

        if data['description']:
            data['description'] = bleach.clean(data['description'], strip=True, tags=ALLOWED_TAGS)

        # Related works will end up with 0 identifiers and end up clogging search with
        # many broken-looking works. Rather than filtering them out, we're setting them to
        # deleted to clean out any stragglers.
        if not data['identifiers']:
            data['is_deleted'] = True

        for agent in data.pop('related_agents'):
            try:
                # We have to try except this. Out of desperation to fix a problem
                # some types got changed to random strings to dodge unique contraints
                self.populate_types(agent)
            except ValueError:
                continue

            for award in agent.get('awards', []):
                self.populate_types(award)

            for affiliation in agent.get('affiliations', []):
                try:
                    # We have to try except this. Out of desperation to fix a problem
                    # some types got changed to random strings to dodge unique contraints
                    self.populate_types(affiliation)
                    affiliation['affiliation'] = apps.get_model(affiliation.pop('affiliation_type'))._meta.verbose_name
                except ValueError:
                    continue

            try:
                # We have to try except this. Out of desperation to fix a problem
                # some types got changed to random strings to dodge unique contraints
                relation_model = apps.get_model(agent.pop('relation_type'))
            except ValueError:
                pass

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

        lineage = []
        for ancestor in data.pop('lineage'):
            self.populate_types(ancestor)
            lineage.insert(0, ancestor)
        if lineage:
            data['lists']['lineage'] = lineage

        data['date'] = (data['date_published'] or data['date_updated'] or data['date_created'])

        return super().post_process(data)


class CreativeWorkShortSubjectsFetcher(CreativeWorkFetcher):
    def post_process(self, data):
        subjects = set()
        for subject in data['subjects']:
            taxonomy, *lineage = subject.split(self.SUBJECT_DELIMITER)
            if taxonomy == settings.SUBJECTS_CENTRAL_TAXONOMY:
                subjects.update(lineage)
        data['subjects'] = list(subjects)

        del data['subject_synonyms']

        return super().post_process(data)


class AgentFetcher(Fetcher):

    QUERY = '''
        SELECT agent.id, json_strip_nulls(json_build_object(
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
                                    , 'related_types', COALESCE(related_types, '{}'))) AS _source
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
        WHERE agent.id IN (SELECT id FROM pks)
    '''

    def post_process(self, data):
        data = super().post_process(data)

        for rtype in data.pop('related_types'):
            try:
                # We have to try except this. Out of desperation to fix a problem
                # some types got changed to random strings to dodge unique contraints
                klass = apps.get_model(rtype)
            except ValueError:
                continue

            for relation_model in klass.__mro__:
                if not relation_model.__mro__[1]._meta.proxy:
                    break
                data['types'].append(relation_model._meta.verbose_name)
        data['types'] = list(set(data['types']))

        return data


class SubjectFetcher(Fetcher):
    QUERY = '''
        SELECT subject.id, json_strip_nulls(json_build_object('id', subject.id , 'name', subject.name)) AS _source
        FROM share_subject AS subject
        WHERE subject.id IN (SELECT id FROM pks)
        AND length(subject.name) < 2001
    '''

    def post_process(self, data):
        return {'id': IDObfuscator.encode_id(data['id'], models.Subject), 'type': 'subject', 'name': data['name']}


class TagFetcher(Fetcher):
    QUERY = '''
        SELECT tag.id, json_strip_nulls(json_build_object('id', tag.id , 'name', tag.name)) AS _source
        FROM share_tag AS tag
        WHERE tag.id IN (SELECT id FROM pks)
        AND length(tag.name) < 2001
    '''

    def post_process(self, data):
        return {'id': IDObfuscator.encode_id(data['id'], models.Tag), 'type': 'tag', 'name': data['name']}
