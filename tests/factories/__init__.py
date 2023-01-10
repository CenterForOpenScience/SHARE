import datetime
import hashlib
import uuid

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
import faker

from project import celery_app

from share import models


fake = faker.Faker()


class ShareUserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda x: '{}{}'.format(fake.name(), x))
    source = factory.RelatedFactory('tests.factories.SourceFactory', 'user')

    class Meta:
        model = models.ShareUser


class NormalizedDataFactory(DjangoModelFactory):
    data = {}
    source = factory.SubFactory(ShareUserFactory)

    class Meta:
        model = models.NormalizedData

    @classmethod
    def _generate(cls, create, attrs):
        normalized_datum = super()._generate(create, attrs)

        # HACK: allow overriding auto_now_add on created_at
        created_at = attrs.pop('created_at', None)
        if created_at is not None:
            normalized_datum.created_at = created_at
            normalized_datum.save()

        return normalized_datum


class SourceFactory(DjangoModelFactory):
    name = factory.Sequence(lambda x: '{}{}'.format(fake.name(), x))
    long_title = factory.Sequence(lambda x: '{}{}'.format(fake.sentence(), x))
    icon = factory.SelfAttribute('name')

    user = factory.SubFactory(ShareUserFactory, source=None)

    class Meta:
        model = models.Source


class ListGenerator(list):

    def __call__(self, *args, **kwargs):
        if hasattr(self, 'side_effect'):
            raise self.side_effect
        return (x for x in self)


class SourceConfigFactory(DjangoModelFactory):
    label = factory.Faker('sentence')
    base_url = factory.Faker('url')
    harvest_after = '00:00'
    source = factory.SubFactory(SourceFactory)

    harvester_key = factory.Faker('word')
    transformer_key = factory.Faker('word')

    class Meta:
        model = models.SourceConfig


class SourceUniqueIdentifierFactory(DjangoModelFactory):
    identifier = factory.Faker('sentence')
    source_config = factory.SubFactory(SourceConfigFactory)

    class Meta:
        model = models.SourceUniqueIdentifier


class RawDatumFactory(DjangoModelFactory):
    datum = factory.Sequence(lambda n: f'{n}{fake.text()}')
    suid = factory.SubFactory(SourceUniqueIdentifierFactory)
    sha256 = factory.LazyAttribute(lambda r: hashlib.sha256(r.datum.encode()).hexdigest())

    class Meta:
        model = models.RawDatum

    @classmethod
    def _generate(cls, create, attrs):
        raw_datum = super()._generate(create, attrs)

        # HACK: allow overriding auto_now_add on date_created
        date_created = attrs.pop('date_created', None)
        if date_created is not None:
            raw_datum.date_created = date_created
            raw_datum.save()

        return raw_datum


class HarvestJobFactory(DjangoModelFactory):
    source_config = factory.SubFactory(SourceConfigFactory)
    start_date = factory.Faker('date_object')
    end_date = factory.LazyAttribute(lambda job: job.start_date + datetime.timedelta(days=1))

    source_config_version = factory.SelfAttribute('source_config.version')
    harvester_version = factory.SelfAttribute('source_config.harvester.version')

    class Meta:
        model = models.HarvestJob


class IngestJobFactory(DjangoModelFactory):
    source_config = factory.SelfAttribute('suid.source_config')
    suid = factory.SelfAttribute('raw.suid')
    raw = factory.SubFactory(RawDatumFactory)
    source_config_version = factory.SelfAttribute('source_config.version')
    transformer_version = factory.SelfAttribute('source_config.transformer.version')
    regulator_version = 1

    class Meta:
        model = models.IngestJob

    @classmethod
    def _generate(cls, create, attrs):
        ingest_job = super()._generate(create, attrs)

        # HACK: allow overriding auto_now_add on date_created
        date_created = attrs.pop('date_created', None)
        if date_created is not None:
            ingest_job.date_created = date_created
            ingest_job.save()

        return ingest_job


class CeleryTaskResultFactory(DjangoModelFactory):
    task_id = factory.Sequence(lambda x: uuid.uuid4())
    task_name = fuzzy.FuzzyChoice(list(celery_app.tasks.keys()))
    status = fuzzy.FuzzyChoice(list(zip(*models.CeleryTaskResult._meta.get_field('status').choices))[0])

    class Meta:
        model = models.CeleryTaskResult


class FormattedMetadataRecordFactory(DjangoModelFactory):
    suid = factory.SubFactory(SourceUniqueIdentifierFactory)

    class Meta:
        model = models.FormattedMetadataRecord
