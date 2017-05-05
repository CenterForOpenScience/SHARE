from unittest import mock
import datetime
import hashlib
import pkg_resources
import uuid

import stevedore

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory

from django.utils import timezone

from project import celery_app

from share import models
from share.harvest import BaseHarvester
from share.transform import BaseTransformer

# TODO move these over
from tests.share.models.factories import NormalizedDataFactory  # noqa
from tests.share.models.factories import AgentFactory as AbstractAgentFactory # noqa
from tests.share.models.factories import WorkIdentifierFactory  # noqa
from tests.share.models.factories import AbstractCreativeWorkFactory  # noqa


class ShareUserFactory(DjangoModelFactory):
    username = factory.Faker('name')
    # long_title = factory.Faker('sentence')

    class Meta:
        model = models.ShareUser


class SourceFactory(DjangoModelFactory):
    name = factory.Faker('sentence')
    long_title = factory.Faker('sentence')
    icon = factory.SelfAttribute('name')

    user = factory.SubFactory(ShareUserFactory)

    class Meta:
        model = models.Source


class ListGenerator(list):

    def __call__(self, *args, **kwargs):
        if hasattr(self, 'side_effect'):
            raise self.side_effect
        return (x for x in self)


class HarvesterFactory(DjangoModelFactory):
    key = factory.Faker('bs')

    class Meta:
        model = models.Harvester

    @factory.post_generation
    def make_harvester(self, create, extracted, **kwargs):
        stevedore.ExtensionManager('share.harvesters')  # Force extensions to load

        class MockHarvester(BaseHarvester):
            KEY = self.key
            VERSION = 1

            _do_fetch = ListGenerator()

        mock_entry = mock.create_autospec(pkg_resources.EntryPoint, instance=True)
        mock_entry.name = self.key
        mock_entry.resolve.return_value = MockHarvester

        stevedore.DriverManager.ENTRY_POINT_CACHE['share.harvesters'].append(mock_entry)


class TransformerFactory(DjangoModelFactory):
    key = factory.Faker('bs')

    class Meta:
        model = models.Transformer

    @factory.post_generation
    def make_transformer(self, create, extracted, **kwargs):
        stevedore.ExtensionManager('share.transformers')  # Force extensions to load

        class MockTransformer(BaseTransformer):
            KEY = self.key
            VERSION = 1

            def do_transform(self, data):
                raise NotImplementedError('Transformers must implement do_transform')

        mock_entry = mock.create_autospec(pkg_resources.EntryPoint, instance=True)
        mock_entry.name = self.key
        mock_entry.module_name = self.key
        mock_entry.resolve.return_value = MockTransformer

        stevedore.DriverManager.ENTRY_POINT_CACHE['share.transformers'].append(mock_entry)


class SourceConfigFactory(DjangoModelFactory):
    label = factory.Faker('sentence')
    base_url = factory.Faker('url')
    source = factory.SubFactory(SourceFactory)

    harvester = factory.SubFactory(HarvesterFactory)
    transformer = factory.SubFactory(TransformerFactory)

    class Meta:
        model = models.SourceConfig


class HarvestLogFactory(DjangoModelFactory):
    source_config = factory.SubFactory(SourceConfigFactory)
    start_date = factory.Faker('date_time')

    class Meta:
        model = models.HarvestLog

    @classmethod
    def _generate(cls, create, attrs):
        attrs['source_config_version'] = attrs['source_config'].version
        attrs['harvester_version'] = attrs['source_config'].harvester.version
        attrs['start_date'] = datetime.datetime.combine(attrs['start_date'].date(), datetime.time(0, 0, 0, 0, timezone.utc))
        attrs['end_date'] = attrs['start_date'] + datetime.timedelta(days=1)
        return super()._generate(create, attrs)


class SourceUniqueIdentifierFactory(DjangoModelFactory):
    identifier = factory.Faker('sentence')
    source_config = factory.SubFactory(SourceConfigFactory)

    class Meta:
        model = models.SourceUniqueIdentifier


class RawDatumFactory(DjangoModelFactory):
    datum = factory.Faker('text')
    suid = factory.SubFactory(SourceUniqueIdentifierFactory)

    class Meta:
        model = models.RawDatum

    @classmethod
    def _generate(cls, create, attrs):
        if 'sha256' not in attrs:
            attrs['sha256'] = hashlib.sha256(attrs.get('datum', '').encode()).hexdigest()

        return super()._generate(create, attrs)


class CeleryTaskResultFactory(DjangoModelFactory):
    task_id = factory.Sequence(lambda x: uuid.uuid4())
    task_name = fuzzy.FuzzyChoice(list(celery_app.tasks.keys()))
    status = fuzzy.FuzzyChoice(list(zip(*models.CeleryTaskResult._meta.get_field('status').choices))[0])

    class Meta:
        model = models.CeleryTaskResult
