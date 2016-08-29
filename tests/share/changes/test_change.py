import pytest

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from share.models import Change
from share.models import Person
from share.models import Preprint
from share.models import Contributor
from share.models import ChangeSet
from share.models import Subject
from share.change import ChangeGraph


@pytest.fixture
def create_graph():
    return ChangeGraph.from_jsonld({
        '@graph': [{
            '@id': '_:1234',
            '@type': 'person',
            'given_name': 'Jane',
            'family_name': 'Doe',
        }]
    }, disambiguate=False)


@pytest.fixture
def create_graph_dependencies():
    return ChangeGraph.from_jsonld({
        '@graph': [{
            '@id': '_:123',
            '@type': 'person',
            'given_name': 'Jane',
            'family_name': 'Doe',
        }, {
            '@id': '_:456',
            '@type': 'contributor',
            'person': {'@id': '_:123', '@type': 'person'},
            'creative_work': {'@id': '_:789', '@type': 'preprint'},
        }, {
            '@id': '_:789',
            '@type': 'preprint',
            'title': 'All About Cats',
        }]
    }, disambiguate=False)


@pytest.fixture
def update_graph(jane_doe):
    return ChangeGraph.from_jsonld({
        '@graph': [{
            '@id': jane_doe.pk,
            '@type': 'person',
            'family_name': 'Dough',
        }]
    })


@pytest.fixture
def merge_graph(jane_doe, john_doe):
    return ChangeGraph.from_jsonld({
        '@graph': [{
            '@id': '_:1234',
            '@type': 'MergeAction',
            'into': {'@id': jane_doe.pk, '@type': 'person'},
            'from': [{'@id': john_doe.pk, '@type': 'person'}]
        }]
    })


class TestChange:

    @pytest.mark.django_db
    def test_create(self, create_graph, change_set):
        change = Change.objects.from_node(create_graph.nodes[0], change_set)

        assert change.type == Change.TYPE.create

        assert change.target is None
        assert change.target_type == ContentType.objects.get(app_label='share', model='person')
        assert change.target_id is None

        assert change.target_version is None
        assert change.target_version_type == ContentType.objects.get(app_label='share', model='personversion')
        assert change.target_version_id is None

        assert change.change == {'given_name': 'Jane', 'family_name': 'Doe'}

    @pytest.mark.django_db
    def test_create_accept(self, create_graph, change_set):
        change = Change.objects.from_node(create_graph.nodes[0], change_set)
        person = change.accept()

        assert person.pk is not None
        assert isinstance(person, Person)
        assert person.versions.first() is not None
        assert person.change == change
        assert person.given_name == 'Jane'
        assert person.family_name == 'Doe'
        assert change.affected_person == person

    @pytest.mark.django_db
    def test_create_accept_no_save(self, create_graph, change_set):
        change = Change.objects.from_node(create_graph.nodes[0], change_set)
        person = change.accept(save=False)

        assert person.pk is None

    @pytest.mark.django_db
    def test_update_accept(self, jane_doe, update_graph, change_set):
        change = Change.objects.from_node(update_graph.nodes[0], change_set)

        assert jane_doe.family_name == 'Doe'

        person = change.accept()
        jane_doe.refresh_from_db()

        assert jane_doe == person
        assert jane_doe.family_name == 'Dough'
        assert len(jane_doe.versions.all()) == 2

    @pytest.mark.django_db
    def test_update_accept_no_save(self, jane_doe, update_graph, change_set):
        change = Change.objects.from_node(update_graph.nodes[0], change_set)

        person = change.accept(save=False)

        assert person.family_name == 'Dough'

        person.refresh_from_db()

        assert person.family_name == 'Doe'
        assert len(jane_doe.versions.all()) == 1


class TestChangeSet:

    @pytest.mark.django_db
    def test_create_dependencies_accept(self, normalized_data_id, create_graph_dependencies):
        change_set = ChangeSet.objects.from_graph(create_graph_dependencies, normalized_data_id)

        assert change_set.changes.count() == 3
        assert change_set.changes.all()[0].node_id == '_:123'
        assert change_set.changes.all()[1].node_id == '_:789'
        assert change_set.changes.all()[2].node_id == '_:456'

        assert change_set.changes.last().change == {
            'person': {'@id': '_:123', '@type': 'person'},
            'creative_work': {'@id': '_:789', '@type': 'preprint'},
        }

        changed = change_set.accept()

        assert len(changed) == 3

        assert isinstance(changed[0], Person)
        assert isinstance(changed[1], Preprint)
        assert isinstance(changed[2], Contributor)

        assert None not in [c.pk for c in changed]

    @pytest.mark.django_db
    def test_update_dependencies_accept(self, john_doe, normalized_data_id):
        graph = ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': john_doe.pk,
                '@type': 'person',
                'given_name': 'Jane',
            }, {
                '@id': '_:456',
                '@type': 'contributor',
                'person': {'@id': john_doe.pk, '@type': 'person'},
                'creative_work': {'@id': '_:789', '@type': 'preprint'},
            }, {
                '@id': '_:789',
                '@type': 'preprint',
                'title': 'All About Cats',
            }]
        })

        change_set = ChangeSet.objects.from_graph(graph, normalized_data_id)

        change_set.accept()

        john_doe.refresh_from_db()

        assert john_doe.given_name == 'Jane'
        assert Preprint.objects.filter(contributor__person=john_doe).count() == 1
        assert Preprint.objects.filter(contributor__person=john_doe).first().title == 'All About Cats'

    # @pytest.mark.django_db
    # def test_merge_accept(self, normalized_data_id, merge_graph, john_doe, jane_doe):
    #     change_set = ChangeSet.objects.from_graph(merge_graph, normalized_data_id)
    #     ChangeSet.objects.from_graph(ChangeGraph.from_jsonld({
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
    #     }), normalized_data_id).accept()

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
    def test_subject_accept(self, normalized_data_id):
        Subject.objects.bulk_create([
            Subject(name='Felines', lineages=[])
        ])

        assert Subject.objects.filter(name='Felines').count() == 1

        graph = ChangeGraph.from_jsonld({
            '@graph': [{
                '@id': '_:987',
                '@type': 'subject',
                'name': 'Felines'
            }, {
                '@id': '_:678',
                '@type': 'throughsubjects',
                'subject': {'@id': '_:987', '@type': 'subject'},
                'creative_work': {'@id': '_:789', '@type': 'preprint'},
            }, {
                '@id': '_:789',
                '@type': 'preprint',
                'title': 'All About Cats',
            }]
        })

        change_set = ChangeSet.objects.from_graph(graph, normalized_data_id)

        change_set.accept()

        assert Preprint.objects.filter(subjects__name='Felines').count() == 1
        assert Preprint.objects.filter(subjects__name='Felines').first().title == 'All About Cats'

    @pytest.mark.django_db
    def test_invalid_subject(self, normalized_data_id):
        with pytest.raises(ValidationError) as e:
            ChangeGraph.from_jsonld({
                '@graph': [{
                    '@id': '_:987',
                    '@type': 'subject',
                    'name': 'Felines'
                }, {
                    '@id': '_:678',
                    '@type': 'throughsubjects',
                    'subject': {'@id': '_:987', '@type': 'subject'},
                    'creative_work': {'@id': '_:789', '@type': 'preprint'},
                }, {
                    '@id': '_:789',
                    '@type': 'preprint',
                    'title': 'All About Cats',
                }]
            })

        assert e.value.message == 'Invalid subject: Felines'
