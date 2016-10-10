import pytest

from share.models import Person
from share.models import Preprint
from share.models import Article
from share.models import PersonIdentifier
from share.models.base import ShareObject
from share.management.commands.maketriggermigrations import Command


@pytest.mark.django_db
def test_build_trigger():
    assert issubclass(Person, ShareObject)

    trigger_build = Command()
    procedure, trigger = trigger_build.build_operations(Person)

    assert trigger.reversible is True
    assert 'DROP TRIGGER share_person_change' in trigger.reverse_sql
    assert 'DROP TRIGGER IF EXISTS share_person_change' in trigger.sql

    assert procedure.reversible is True
    assert 'DROP FUNCTION before_share_person_change' in procedure.reverse_sql
    assert 'CREATE OR REPLACE FUNCTION before_share_person_change' in procedure.sql


class TestVersioning:

    @pytest.mark.django_db
    def test_timestamping(share_source, change_ids):
        p = Person(given_name='John', family_name='Doe', change_id=change_ids.get())
        p.save()

        created, modified = p.date_created, p.date_modified

        assert (p.date_created - p.date_modified).total_seconds() < 1

        p.given_name = 'Jane'
        p.change_id = change_ids.get()
        p.save()

        assert modified < p.date_modified
        assert created == p.date_created

    @pytest.mark.django_db
    def test_creates_version(share_source, change_ids):
        p = Person(given_name='John', family_name='Doe', change_id=change_ids.get())
        p.save()
        p.refresh_from_db()

        assert isinstance(p.version, Person.VersionModel)

    @pytest.mark.django_db
    def test_simple(self, change_ids):
        p = Person(given_name='John', family_name='Doe', change_id=change_ids.get())
        p.save()

        p.given_name = 'Jane'
        p.change_id = change_ids.get()
        p.save()

        assert p.versions.all()[0].given_name == 'Jane'
        assert p.versions.all()[1].given_name == 'John'

    @pytest.mark.django_db
    def test_many_versions(self, change_ids):
        p = Person(given_name='John', family_name='Doe', change_id=change_ids.get())
        p.save()

        names = ['Jane', 'John', 'Jone', 'Jane', 'James', 'Joe', 'Jim', 'Jack', 'Jacklynn']

        for name in names:
            p.given_name = name
            p.change_id = change_ids.get()
            p.save()

        for i, name in enumerate(reversed(['John'] + names)):
            assert p.versions.all()[i].given_name == name

    @pytest.mark.django_db
    def test_relations(self, john_doe, change_ids):
        ident = PersonIdentifier.objects.create(
            uri='http://dinosaurs.sexy/john_doe',
            person=john_doe,
            person_version=john_doe.version,
            change_id=change_ids.get()
        )

        ident.refresh_from_db()
        john_doe.refresh_from_db()

        assert john_doe.personidentifiers.count() == 1

        assert john_doe == ident.person
        assert john_doe.version == ident.person_version

    @pytest.mark.django_db
    def test_relations_related_changed(self, john_doe, change_ids):
        ident = PersonIdentifier.objects.create(
            uri='http://dinosaurs.sexy/john_doe',
            person=john_doe,
            person_version=john_doe.version,
            change_id=change_ids.get()
        )

        ident.refresh_from_db()
        john_doe.refresh_from_db()

        john_doe.given_name = 'James'
        john_doe.change_id = change_ids.get()
        john_doe.save()
        john_doe.refresh_from_db()

        assert john_doe.personidentifiers.count() == 1

        assert john_doe == ident.person
        assert john_doe.version != ident.person_version
        assert john_doe.versions.last() == ident.person_version

        assert ident == john_doe.personidentifiers.first()


@pytest.mark.django_db
class TestAdministrativeChange:

    def test_must_change(self, john_doe):
        with pytest.raises(AssertionError) as e:
            john_doe.administrative_change()
        assert e.value.args == ('Don\'t make empty changes', )

    def test_works(self, john_doe):
        john_doe.refresh_from_db()  # load version

        assert john_doe.versions.count() == 1
        assert john_doe.given_name == 'John'
        john_doe.administrative_change(given_name='Jane')
        assert john_doe.given_name == 'Jane'
        assert john_doe.versions.count() == 2
        assert john_doe.change.change_set.normalized_data.source.username == 'system'

    def test_invalid_attribute(self, john_doe):
        john_doe.refresh_from_db()  # load version

        with pytest.raises(AttributeError) as e:
            john_doe.administrative_change(favorite_animal='Anteater')
        assert e.value.args == ('favorite_animal', )

    def test_transition_types(self, all_about_anteaters):
        all_about_anteaters.refresh_from_db()  # load version

        assert all_about_anteaters.type == 'share.article'
        all_about_anteaters.administrative_change(type='share.preprint')
        assert all_about_anteaters.type == 'share.preprint'

        with pytest.raises(Article.DoesNotExist):
            all_about_anteaters.refresh_from_db()
        assert Preprint.objects.get(pk=all_about_anteaters.pk)
