import factory
import faker
from factory.django import DjangoModelFactory

from share import models

__all__ = (
    'SourceFactory',
    'ShareUserFactory',
    'NormalizedDataFactory',
)

faker = faker.Faker()


class ShareUserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda x: '{}{}'.format(faker.name(), x))
    source = factory.RelatedFactory('tests.factories.core.SourceFactory', 'user')

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
    name = factory.Sequence(lambda x: '{}{}'.format(faker.name(), x))
    long_title = factory.Sequence(lambda x: '{}{}'.format(faker.sentence(), x))
    icon = factory.SelfAttribute('name')

    user = factory.SubFactory(ShareUserFactory, source=None)

    class Meta:
        model = models.Source
