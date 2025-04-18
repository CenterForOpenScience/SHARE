import hashlib
import uuid

import factory
from factory import fuzzy
from factory.django import DjangoModelFactory
import faker

from project import celery_app

from share import models as share_db
from trove import models as trove_db


fake = faker.Faker()


class ShareUserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda x: '{}{}'.format(fake.name(), x))
    source = factory.RelatedFactory('tests.factories.SourceFactory', 'user')

    class Meta:
        model = share_db.ShareUser


class SourceFactory(DjangoModelFactory):
    name = factory.Sequence(lambda x: '{}{}'.format(fake.name(), x))
    long_title = factory.Sequence(lambda x: '{}{}'.format(fake.sentence(), x))

    user = factory.SubFactory(ShareUserFactory, source=None)

    class Meta:
        model = share_db.Source


class SourceConfigFactory(DjangoModelFactory):
    label = factory.Faker('sentence')
    base_url = factory.Faker('url')
    source = factory.SubFactory(SourceFactory)
    transformer_key = None

    class Meta:
        model = share_db.SourceConfig


class SourceUniqueIdentifierFactory(DjangoModelFactory):
    identifier = factory.Faker('sentence')
    source_config = factory.SubFactory(SourceConfigFactory)

    class Meta:
        model = share_db.SourceUniqueIdentifier


class RawDatumFactory(DjangoModelFactory):
    datum = factory.Sequence(lambda n: f'{n}{fake.text()}')
    suid = factory.SubFactory(SourceUniqueIdentifierFactory)
    sha256 = factory.LazyAttribute(lambda r: hashlib.sha256(r.datum.encode()).hexdigest())

    class Meta:
        model = share_db.RawDatum

    @classmethod
    def _generate(cls, create, attrs):
        raw_datum = super()._generate(create, attrs)

        # HACK: allow overriding auto_now_add on date_created
        date_created = attrs.pop('date_created', None)
        if date_created is not None:
            raw_datum.date_created = date_created
            raw_datum.save()

        return raw_datum


class CeleryTaskResultFactory(DjangoModelFactory):
    task_id = factory.Sequence(lambda x: uuid.uuid4())
    task_name = fuzzy.FuzzyChoice(list(celery_app.tasks.keys()))
    status = fuzzy.FuzzyChoice(list(zip(*share_db.CeleryTaskResult._meta.get_field('status').choices))[0])

    class Meta:
        model = share_db.CeleryTaskResult


###
# trove models

class ResourceIdentifierFactory(DjangoModelFactory):
    sufficiently_unique_iri = factory.Sequence(lambda x: f'://test.example/{x}')
    scheme_list = ['foo']

    class Meta:
        model = trove_db.ResourceIdentifier


class IndexcardFactory(DjangoModelFactory):
    source_record_suid = factory.SubFactory(SourceUniqueIdentifierFactory)

    class Meta:
        model = trove_db.Indexcard


class LatestIndexcardRdfFactory(DjangoModelFactory):
    from_raw_datum = factory.SubFactory(RawDatumFactory)
    indexcard = factory.SubFactory(IndexcardFactory)
    focus_iri = factory.Sequence(lambda x: f'http://test.example/{x}')
    rdf_as_turtle = factory.Sequence(lambda x: f'<http://test.example/{x}> a <http://text.example/Greeting>')
    # turtle_checksum_iri =

    class Meta:
        model = trove_db.LatestIndexcardRdf


class DerivedIndexcardFactory(DjangoModelFactory):
    upriver_indexcard = factory.SubFactory(IndexcardFactory)
    deriver_identifier = factory.SubFactory(ResourceIdentifierFactory)
    derived_text = 'hello'
    # derived_checksum_iri =

    class Meta:
        model = trove_db.DerivedIndexcard
