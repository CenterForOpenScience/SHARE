import factory
from factory.django import DjangoModelFactory

from share import models


class ShareUserFactory(DjangoModelFactory):
    username = factory.Faker('first_name')
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
    key = factory.Faker('word')

    class Meta:
        model = models.Harvester


class TransformerFactory(DjangoModelFactory):
    key = factory.Faker('word')

    class Meta:
        model = models.Transformer


class SourceConfigFactory(DjangoModelFactory):
    label = factory.Faker('word')
    base_url = factory.Faker('url')
    source = factory.SubFactory(SourceFactory)

    harvester = factory.SubFactory(HarvesterFactory)
    transformer = factory.SubFactory(TransformerFactory)

    class Meta:
        model = models.SourceConfig
