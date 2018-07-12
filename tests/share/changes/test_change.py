import pytest

from django.contrib.contenttypes.models import ContentType

from share import models
from share.ingest.change_builder import ChangeBuilder
from share.util import IDObfuscator
from share.util.graph import MutableGraph


@pytest.fixture
def create_graph():
    return MutableGraph.from_jsonld([{
        '@id': '_:1234',
        '@type': 'person',
        'given_name': 'Jane',
        'family_name': 'Doe',
    }])


@pytest.fixture
def create_graph_node(create_graph):
    return next(n for n in create_graph)


@pytest.fixture
def create_graph_dependencies():
    return MutableGraph.from_jsonld([{
        '@id': '_:123',
        '@type': 'person',
        'given_name': 'Jane',
        'family_name': 'Doe',
    }, {
        '@id': '_:456',
        '@type': 'Creator',
        'agent': {'@id': '_:123', '@type': 'person'},
        'creative_work': {'@id': '_:789', '@type': 'preprint'},
    }, {
        '@id': '_:789',
        '@type': 'preprint',
        'title': 'All About Cats',
        'related_agents': [{'@id': '_:456', '@type': 'Creator'}]
    }])


@pytest.fixture
def update_graph(jane_doe):
    return MutableGraph.from_jsonld([{
        '@id': IDObfuscator.encode(jane_doe),
        '@type': 'person',
        'family_name': 'Dough',
    }])


@pytest.fixture
def update_graph_node(update_graph):
    return next(n for n in update_graph)


# @pytest.fixture
# def merge_graph(jane_doe, john_doe):
#     return MutableGraph.from_jsonld.from_jsonld({
#         '@graph': [{
#             '@id': '_:1234',
#             '@type': 'MergeAction',
#             'into': {'@id': IDObfuscator.encode(jane_doe), '@type': 'person'},
#             'from': [{'@id': IDObfuscator.encode(john_doe), '@type': 'person'}]
#         }]
#     })


class TestChange:

    @pytest.mark.django_db
    def test_create(self, create_graph_node, change_set):
        change = ChangeBuilder(create_graph_node).build_change(change_set)

        assert change.type == models.Change.TYPE.create

        assert change.target is None
        assert change.target_type == ContentType.objects.get(app_label='share', model='abstractagent')
        assert change.target_id is None

        assert change.target_version is None
        assert change.target_version_type == ContentType.objects.get(app_label='share', model='abstractagentversion')
        assert change.target_version_id is None

        assert change.change == {'given_name': 'Jane', 'family_name': 'Doe'}

    @pytest.mark.django_db
    def test_create_accept(self, create_graph_node, change_set):
        change = ChangeBuilder(create_graph_node).build_change(change_set)
        person = change.accept()

        assert person.pk is not None
        assert isinstance(person, models.Person)
        assert person.versions.first() is not None
        assert person.change == change
        assert person.given_name == 'Jane'
        assert person.family_name == 'Doe'
        assert change.affected_abstractagent == person

    @pytest.mark.django_db
    def test_create_accept_no_save(self, create_graph_node, change_set):
        change = ChangeBuilder(create_graph_node).build_change(change_set)
        person = change.accept(save=False)

        assert person.pk is None

    @pytest.mark.django_db
    def test_update_accept(self, jane_doe, update_graph_node, change_set):
        change = ChangeBuilder(
            update_graph_node,
            instance_map={update_graph_node: jane_doe},
        ).build_change(change_set)

        assert jane_doe.family_name == 'Doe'

        person = change.accept()
        jane_doe.refresh_from_db()

        assert jane_doe == person
        assert jane_doe.family_name == 'Dough'
        assert len(jane_doe.versions.all()) == 2

    @pytest.mark.django_db
    def test_update_accept_no_save(self, jane_doe, update_graph_node, change_set):
        change = ChangeBuilder(
            update_graph_node,
            instance_map={update_graph_node: jane_doe},
        ).build_change(change_set)

        person = change.accept(save=False)

        assert person.family_name == 'Dough'

        person.refresh_from_db()

        assert person.family_name == 'Doe'
        assert len(jane_doe.versions.all()) == 1
        assert jane_doe.version == jane_doe.versions.first()


class TestChangeSet:

    @pytest.mark.django_db
    def test_create_dependencies_accept(self, normalized_data, create_graph_dependencies):
        change_set = ChangeBuilder.build_change_set(create_graph_dependencies, normalized_data)

        assert change_set.changes.count() == 3
        assert change_set.changes.all()[0].node_id == '_:123'
        assert change_set.changes.all()[1].node_id == '_:789'
        assert change_set.changes.all()[2].node_id == '_:456'

        assert change_set.changes.last().change == {
            'agent': {'@id': '_:123', '@type': 'person'},
            'creative_work': {'@id': '_:789', '@type': 'preprint'},
        }

        changed = change_set.accept()

        assert len(changed) == 3

        assert isinstance(changed[0], models.Person)
        assert isinstance(changed[1], models.Preprint)
        assert isinstance(changed[2], models.Creator)

        assert None not in [c.pk for c in changed]

    @pytest.mark.django_db
    def test_update_dependencies_accept(self, john_doe, normalized_data):
        john_doe_id = IDObfuscator.encode(john_doe)
        graph = MutableGraph.from_jsonld([{
            '@id': john_doe_id,
            '@type': 'person',
            'given_name': 'Jane',
        }, {
            '@id': '_:456',
            '@type': 'Creator',
            'agent': {'@id': john_doe_id, '@type': 'person'},
            'creative_work': {'@id': '_:789', '@type': 'preprint'},
        }, {
            '@id': '_:789',
            '@type': 'preprint',
            'title': 'All About Cats',
        }])

        change_set = ChangeBuilder.build_change_set(graph, normalized_data, instance_map={
            john_doe_id: john_doe,
        })

        change_set.accept()

        john_doe.refresh_from_db()

        assert john_doe.given_name == 'Jane'
        assert models.Preprint.objects.filter(agent_relations__agent=john_doe).count() == 1
        assert models.Preprint.objects.filter(agent_relations__agent=john_doe).first().title == 'All About Cats'

    @pytest.mark.django_db
    def test_can_delete_work(self, john_doe, normalized_data):
        graph = MutableGraph.from_jsonld([{
            '@id': '_:abc',
            '@type': 'workidentifier',
            'uri': 'http://osf.io/faq',
            'creative_work': {'@id': '_:789', '@type': 'preprint'}
        }, {
            '@id': '_:789',
            '@type': 'preprint',
            'title': 'All About Cats',
        }])

        change_set = ChangeBuilder.build_change_set(graph, normalized_data, disambiguate=True)

        preprint, identifier = change_set.accept()

        assert preprint.is_deleted is False

        graph = MutableGraph.from_jsonld([{
            '@id': '_:abc',
            '@type': 'workidentifier',
            'uri': 'http://osf.io/faq',
            'creative_work': {'@id': '_:789', '@type': 'preprint'}
        }, {
            '@id': '_:789',
            'is_deleted': True,
            '@type': 'preprint',
        }])

        ChangeBuilder.build_change_set(graph, normalized_data, disambiguate=True).accept()

        preprint.refresh_from_db()
        assert preprint.is_deleted is True

    # @pytest.mark.django_db
    # def test_merge_accept(self, normalized_data, merge_graph, john_doe, jane_doe):
    #     change_set = ChangeSet.objects.from_graph(merge_graph, normalized_data)
    #     ChangeSet.objects.from_graph(MutableGraph.from_jsonld({
    #         '@graph': [{
    #             '@id': '_:123',
    #             '@type': 'preprint',
    #             'title': 'All About Cats'
    #         }, {
    #             '@id': '_:456',
    #             '@type': 'contributor',
    #             'person': {'@id': john_doe.pk, '@type': 'person'},
    #             'creative_work': {'@id': '_:123', '@type': 'preprint'},
    #         }]
    #     }), normalized_data).accept()

    #     assert Preprint.objects.filter(contributor__person=john_doe).count() == 1
    #     assert Preprint.objects.filter(contributor__person=john_doe).count() == 1
    #     assert Preprint.objects.filter(contributor__person=jane_doe).count() == 0

    #     change_set.accept()

    #     john_doe.refresh_from_db()
    #     jane_doe.refresh_from_db()

    #     # Jane should not have been modified
    #     assert jane_doe.same_as is None
    #     assert jane_doe.versions.count() == 1

    #     # John should have been updated
    #     assert john_doe.versions.count() == 2

    #     # John's same_as field and same_as_version should have been updated
    #     assert john_doe.same_as == jane_doe
    #     assert john_doe.version.same_as == jane_doe
    #     assert john_doe.same_as_version == jane_doe.version
    #     assert john_doe.version.same_as_version == jane_doe.version

    #     # John's latest change should be set to the  merge change
    #     assert john_doe.change.change_set == change_set
    #     assert john_doe.version.change.change_set == change_set

    #     # Ensure that date modifieds have been update
    #     assert john_doe.versions.first().date_modified > john_doe.versions.last().date_modified

    #     # John is no longer a contributor on anything
    #     assert Preprint.objects.filter(contributor__person=john_doe).count() == 0
    #     assert Preprint.objects.filter(contributor__person_version=john_doe.version).count() == 0

    #     # Jane is now a contributor
    #     assert Preprint.objects.filter(contributor__person=jane_doe).count() == 1
    #     assert Preprint.objects.filter(contributor__person_version=jane_doe.version).count() == 1

    #     # The affected contributor should have been updated
    #     assert Contributor.objects.get(person=jane_doe).versions.count() == 2
    #     assert Contributor.objects.get(person=jane_doe).change.change_set == change_set

    @pytest.mark.django_db
    def test_change_work_type(self, normalized_data):
        '''
        A CreativeWork with an Identifier exists. Accept a new changeset
        with a Preprint with the same Identifier. The preprint should
        disambiguate to the existing work, and the work's type should be
        updated to Preprint
        '''
        title = 'Ambiguous Earthquakes'
        uri = 'http://osf.io/special-snowflake'

        cg = MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'project',
            'title': title,
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'project'}
        }])

        original_change_set = ChangeBuilder.build_change_set(cg, normalized_data, disambiguate=True)

        work, identifier = original_change_set.accept()
        id = work.id

        assert identifier.uri == uri
        assert models.Project.objects.count() == 1
        assert models.Preprint.objects.count() == 0
        assert models.CreativeWork.objects.count() == 1
        assert models.Project.objects.all()[0].changes.count() == 1

        cg = MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'preprint',
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'preprint'}
        }])

        change_set = ChangeBuilder.build_change_set(cg, normalized_data, disambiguate=True)

        change_set.accept()

        assert models.Project.objects.count() == 0
        assert models.Preprint.objects.count() == 1
        assert models.CreativeWork.objects.count() == 1
        assert models.Preprint.objects.get(id=id).title == title
        assert models.Preprint.objects.all()[0].changes.count() == 2

    @pytest.mark.django_db
    def test_generic_creative_work(self, normalized_data):
        '''
        A Preprint with an Identifier exists. Accept a changeset with a
        CreativeWork with the same Identifier and a different title.
        The Preprint's title should be updated to the new value, but its type
        should remain the same.
        '''
        old_title = 'Ambiguous Earthquakes'
        uri = 'http://osf.io/special-snowflake'

        original_change_set = ChangeBuilder.build_change_set(MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'preprint',
            'title': old_title,
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'preprint'}
        }]), normalized_data)

        preprint, identifier = original_change_set.accept()
        id = preprint.id

        assert identifier.uri == uri
        assert models.Preprint.objects.count() == 1
        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 0
        assert models.Preprint.objects.get(id=id).title == old_title

        new_title = 'Ambidextrous Earthquakes'

        graph = MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'creativework',
            'title': new_title,
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'creativework'}
        }])

        change_set = ChangeBuilder.build_change_set(graph, normalized_data, disambiguate=True)
        change_set.accept()

        assert models.Preprint.objects.count() == 1
        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 0
        assert models.Preprint.objects.get(id=id).title == new_title

    @pytest.mark.django_db
    def test_related_works(self, normalized_data):
        '''
        Create two works with a relation between them.
        '''
        uri = 'http://osf.io/special-snowflake'

        change_set = ChangeBuilder.build_change_set(MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'preprint',
            'title': 'Dogs are okay too',
            'related_works': [{'@id': '_:foo', '@type': 'cites'}]
        }, {
            '@id': '_:2345',
            '@type': 'creativework',
            'title': 'Cats, tho',
            'identifiers': [{'@id': '_:4567', '@type': 'workidentifier'}]
        }, {
            '@id': '_:foo',
            '@type': 'cites',
            'subject': {'@id': '_:1234', '@type': 'preprint'},
            'related': {'@id': '_:2345', '@type': 'creativework'},
        }, {
            '@id': '_:4567',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:2345', '@type': 'creativework'}
        }]), normalized_data)
        change_set.accept()

        assert models.Preprint.objects.count() == 1
        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 1

        p = models.Preprint.objects.first()
        c = models.AbstractCreativeWork.objects.get(title='Cats, tho')

        assert p.related_works.count() == 1
        assert p.related_works.first() == c
        assert p.outgoing_creative_work_relations.count() == 1
        assert p.outgoing_creative_work_relations.first()._meta.model_name == 'cites'
        assert p.outgoing_creative_work_relations.first().related == c
        assert c.incoming_creative_work_relations.count() == 1
        assert c.incoming_creative_work_relations.first()._meta.model_name == 'cites'
        assert c.incoming_creative_work_relations.first().subject == p

    @pytest.mark.django_db
    def test_add_relation_related(self, normalized_data):
        '''
        A work exists. Add a second work with a relation to the first work.
        The first work should have the appropriate inverse relation to the
        second work.
        '''

        uri = 'http://osf.io/special-snowflake'
        ChangeBuilder.build_change_set(MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'article',
            'title': 'All About Cats',
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'article'}
        }]), normalized_data).accept()

        assert models.Article.objects.count() == 1

        graph = MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'preprint',
            'title': 'Dogs are okay too',
            'related_works': [{'@id': '_:foo', '@type': 'cites'}]
        }, {
            '@id': '_:foo',
            '@type': 'cites',
            'subject': {'@id': '_:1234', '@type': 'preprint'},
            'related': {'@id': '_:2345', '@type': 'creativework'},
        }, {
            '@id': '_:2345',
            '@type': 'creativework',
            'identifiers': [{'@id': '_:4567', '@type': 'workidentifier'}]
        }, {
            '@id': '_:4567',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:2345', '@type': 'creativework'}
        }])
        change_set = ChangeBuilder.build_change_set(graph, normalized_data, disambiguate=True)
        change_set.accept()

        assert models.Article.objects.count() == 1
        assert models.Preprint.objects.count() == 1
        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 0

        cat = models.Article.objects.first()
        dog = models.Preprint.objects.first()

        assert dog.outgoing_creative_work_relations.count() == 1
        assert dog.outgoing_creative_work_relations.first()._meta.model_name == 'cites'
        assert dog.outgoing_creative_work_relations.first().related == cat
        assert cat.incoming_creative_work_relations.count() == 1
        assert cat.incoming_creative_work_relations.first()._meta.model_name == 'cites'
        assert cat.incoming_creative_work_relations.first().subject == dog

    @pytest.mark.django_db
    def test_add_work_with_existing_relation(self, normalized_data):
        '''
        Harvest a work that has a relation to some work identified by a DOI.
        The related work should be a CreativeWork with no information except
        the one Identifier.
        Then harvest a work with the same DOI. It should update the
        CreativeWork's type and attributes instead of creating a new work.
        '''

        uri = 'http://osf.io/special-snowflake'

        ChangeBuilder.build_change_set(MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'preprint',
            'title': 'Dogs are okay',
            'related_works': [{'@id': '_:foo', '@type': 'cites'}]
        }, {
            '@id': '_:foo',
            '@type': 'cites',
            'subject': {'@id': '_:1234', '@type': 'preprint'},
            'related': {'@id': '_:2345', '@type': 'creativework'},
        }, {
            '@id': '_:2345',
            '@type': 'creativework',
            'identifiers': [{'@id': '_:4567', '@type': 'workidentifier'}]
        }, {
            '@id': '_:4567',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:2345', '@type': 'creativework'}
        }]), normalized_data).accept()

        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 1
        assert models.Preprint.objects.count() == 1
        assert models.Article.objects.count() == 0

        change = MutableGraph.from_jsonld([{
            '@id': '_:1234',
            '@type': 'article',
            'title': 'All About Cats',
            'identifiers': [{'@id': '_:2345', '@type': 'workidentifier'}]
        }, {
            '@id': '_:2345',
            '@type': 'workidentifier',
            'uri': uri,
            'creative_work': {'@id': '_:1234', '@type': 'article'}
        }])

        ChangeBuilder.build_change_set(change, normalized_data, disambiguate=True).accept()

        assert models.CreativeWork.objects.filter(type='share.creativework').count() == 0
        assert models.Article.objects.count() == 1
        assert models.Preprint.objects.count() == 1

        cat = models.Article.objects.first()
        dog = models.Preprint.objects.first()

        assert dog.outgoing_creative_work_relations.count() == 1
        assert dog.outgoing_creative_work_relations.first()._meta.model_name == 'cites'
        assert dog.outgoing_creative_work_relations.first().related == cat
        assert cat.incoming_creative_work_relations.count() == 1
        assert cat.incoming_creative_work_relations.first()._meta.model_name == 'cites'
        assert cat.incoming_creative_work_relations.first().subject == dog

    @pytest.mark.django_db
    def test_ignore_generic_work_type(self, change_factory, all_about_anteaters):
        cs = change_factory.from_graph({
            '@graph': [{
                '@id': IDObfuscator.encode(all_about_anteaters),
                '@type': 'creativework'
            }]
        }, disambiguate=True)

        assert cs is None

    @pytest.mark.django_db
    def test_work_type_stays_nongeneric(self, change_factory, all_about_anteaters):
        new_title = 'Some about Anteaters'
        cs = change_factory.from_graph({
            '@graph': [{
                '@id': IDObfuscator.encode(all_about_anteaters),
                '@type': 'creativework',
                'title': new_title
            }]
        }, disambiguate=True)

        assert all_about_anteaters.type == 'share.article'
        assert models.Publication.objects.count() == 1

        cs.accept()
        all_about_anteaters.refresh_from_db()

        assert all_about_anteaters.type == 'share.article'
        assert all_about_anteaters.title == new_title

    @pytest.mark.django_db
    def test_change_agent_type(self, change_factory, university_of_whales):
        cs = change_factory.from_graph({
            '@graph': [{
                '@id': IDObfuscator.encode(university_of_whales),
                '@type': 'consortium'
            }]
        }, disambiguate=True)

        assert models.Institution.objects.count() == 1
        assert models.Consortium.objects.count() == 0

        (org,) = cs.accept()

        assert org.type == 'share.consortium'
        assert org.id == university_of_whales.id
        assert org.name == university_of_whales.name
        assert models.Institution.objects.count() == 0
        assert models.Consortium.objects.count() == 1
