import pkg_resources
from unittest import mock
import stevedore

import factory
from factory.django import DjangoModelFactory

from share import models
from share.harvest import BaseHarvester
from share.transform import BaseTransformer


class ShareUserFactory(DjangoModelFactory):
    username = factory.Faker('name')
    # long_title = factory.Faker('sentence')

    class Meta:
        model = models.ShareUser


class SourceFactory(DjangoModelFactory):
    name = factory.Faker('company')
    long_title = factory.Faker('sentence')

    user = factory.SubFactory(ShareUserFactory)

    class Meta:
        model = models.Source


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

            do_harvest = mock.Mock(return_value=[])

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
