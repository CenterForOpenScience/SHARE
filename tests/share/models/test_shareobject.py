import pytest

from share import models
from share.management.commands.maketriggermigrations import Command
from share.models import AgentIdentifier
from share.models import Article
from share.models import Person
from share.models import Preprint
from share.models.base import ShareObject

from tests import factories


@pytest.mark.django_db
def test_build_trigger():
    assert issubclass(Person, ShareObject)

    trigger_build = Command()
    procedure, trigger = trigger_build.build_operations(Person)

    assert trigger.reversible is True
    assert 'DROP TRIGGER share_agent_change' in trigger.reverse_sql
    assert 'DROP TRIGGER IF EXISTS share_agent_change' in trigger.sql

    assert procedure.reversible is True
    assert 'DROP FUNCTION before_share_agent_change' in procedure.reverse_sql
    assert 'CREATE OR REPLACE FUNCTION before_share_agent_change' in procedure.sql


class TestVersioning:

    @pytest.mark.django_db
    def test_timestamping(self, change_ids):
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
    def test_creates_version(self, change_ids):
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

        p.refresh_from_db()
        assert p.versions.first() == p.version

        for i, name in enumerate(reversed(['John'] + names)):
            assert p.versions.all()[i].given_name == name

    @pytest.mark.django_db
    def test_relations(self, john_doe, change_ids):
        ident = AgentIdentifier.objects.create(
            uri='http://dinosaurs.sexy/john_doe',
            agent=john_doe,
            agent_version=john_doe.version,
            change_id=change_ids.get()
        )

        ident.refresh_from_db()
        john_doe.refresh_from_db()

        assert john_doe.identifiers.count() == 1

        assert john_doe == ident.agent
        assert john_doe.version == ident.agent_version

    @pytest.mark.django_db
    def test_relations_related_changed(self, john_doe, change_ids):
        ident = AgentIdentifier.objects.create(
            uri='http://dinosaurs.sexy/john_doe',
            agent=john_doe,
            agent_version=john_doe.version,
            change_id=change_ids.get()
        )

        ident.refresh_from_db()
        john_doe.refresh_from_db()

        john_doe.given_name = 'James'
        john_doe.change_id = change_ids.get()
        john_doe.save()
        john_doe.refresh_from_db()

        assert john_doe.identifiers.count() == 1

        assert john_doe == ident.agent
        assert john_doe.version != ident.agent_version
        assert john_doe.versions.last() == ident.agent_version

        assert ident == john_doe.identifiers.first()


@pytest.mark.django_db
class TestAdministrativeChange:

    def test_must_change(self, john_doe):
        with pytest.raises(ValueError) as e:
            john_doe.administrative_change()
        assert e.value.args == ('Pass allow_empty=True to allow empty changes', )

    def test_allow_empty(self, john_doe):
        john_doe.administrative_change(allow_empty=True)

    def test_works(self, john_doe):
        assert john_doe.version == john_doe.versions.first()
        assert john_doe.versions.count() == 1
        assert john_doe.given_name == 'John'
        john_doe.administrative_change(given_name='Jane')
        assert john_doe.given_name == 'Jane'
        assert john_doe.versions.count() == 2
        assert john_doe.change.change_set.normalized_data.source.username == 'system'

    def test_invalid_attribute(self, john_doe):
        with pytest.raises(AttributeError) as e:
            john_doe.administrative_change(favorite_animal='Anteater')
        assert e.value.args == ('favorite_animal', )

    def test_transition_types(self, all_about_anteaters):
        assert all_about_anteaters.type == 'share.article'
        all_about_anteaters.administrative_change(type='share.preprint')
        assert all_about_anteaters.type == 'share.preprint'

        with pytest.raises(Article.DoesNotExist):
            all_about_anteaters.refresh_from_db()
        assert Preprint.objects.get(pk=all_about_anteaters.pk)

    def test_related_objects(self):
        work = factories.AbstractCreativeWorkFactory()
        identifier = factories.WorkIdentifierFactory()

        assert identifier.creative_work != work

        identifier.administrative_change(creative_work=work)
        identifier.refresh_from_db()

        assert identifier.creative_work == work


@pytest.mark.django_db
class TestDefrankenize:

    def test_must_be_really_sure_about_it(self):
        work = factories.AbstractCreativeWorkFactory()

        with pytest.raises(ValueError) as e:
            work.defrankenize()
        assert e.value.args == ('You have to be really sure about this', )

        with pytest.raises(ValueError) as e:
            work.defrankenize(True)
        assert e.value.args == ('You have to be really sure about this', )

        work.defrankenize(im_really_sure_about_this=True)

    def test_resets_name(self):
        work = factories.AbstractCreativeWorkFactory(title='This is a franken', is_deleted=False)

        work.defrankenize(im_really_sure_about_this=True)

        assert work.title == 'Defrankenized work'
        assert work.is_deleted is True

    @pytest.mark.parametrize('agents', [0, 5])
    @pytest.mark.parametrize('idents', [0, 5])
    @pytest.mark.parametrize('iworks', [0, 5])
    @pytest.mark.parametrize('oworks', [0, 5])
    @pytest.mark.parametrize('tags', [0, 5])
    def test_removes_relations(self, idents, agents, oworks, iworks, tags):
        work = factories.AbstractCreativeWorkFactory(title='This is a franken', is_deleted=False)

        factories.WorkIdentifierFactory.create_batch(idents, creative_work=work)
        factories.AgentWorkRelationFactory.create_batch(agents, creative_work=work)
        factories.AbstractWorkRelationFactory.create_batch(iworks, subject=work)
        factories.AbstractWorkRelationFactory.create_batch(oworks, related=work)
        factories.ThroughTagsFactory.create_batch(tags, creative_work=work)

        work.defrankenize(im_really_sure_about_this=True)

        assert work.is_deleted is True
        assert work.title == 'Defrankenized work'

        # We want to keep these around for now
        assert work.changes.exists() is True
        assert work.versions.exists() is True

        # Didn't delete any agents
        assert models.AbstractAgent.objects.count() == agents
        assert models.Tag.objects.count() == tags
        assert models.AbstractCreativeWork.objects.count() == 1 + oworks + iworks

        for field in models.AbstractCreativeWork._meta.get_fields():
            if not field.one_to_many or field.name in ('changes', 'versions'):
                continue

            assert getattr(work, field.get_accessor_name()).count() == 0
