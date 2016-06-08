import pytest
from datetime import datetime

from django.db import models
from django.db import connection

from share.models import Person
from share.models.base import ShareObject
from share.management.commands.build_triggers import Command


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


@pytest.mark.django_db
def test_timestamping(share_user):
    p = Person(given_name='John', family_name='Doe', source=share_user)
    p.save()

    now = datetime.utcnow().replace(tzinfo=p.changed_at.tzinfo)
    created, changed = p.created_at, p.changed_at

    assert (p.created_at - p.changed_at).total_seconds() < 1

    p.given_name = 'Jane'
    p.save()

    assert changed < p.changed_at
    assert created == p.created_at


@pytest.mark.django_db
def test_create_version(share_user):
    p = Person(given_name='John', family_name='Doe', source=share_user)
    p.save()
    p.refresh_from_db()

    assert isinstance(p.version, Person.VersionModel)


@pytest.mark.django_db
def test_versioning(share_user):
    p = Person(given_name='John', family_name='Doe', source=share_user)
    p.save()

    p.given_name = 'Jane'
    p.save()

    assert p.versions.all()[0].given_name == 'Jane'
    assert p.versions.all()[1].given_name == 'John'
