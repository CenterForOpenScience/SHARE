import pytest

from django.apps import apps

from share import models
from share.harvest.base import FetchResult

from tests.share.models import factories
from tests.share.normalize.factories import *


@pytest.mark.django_db
class TestDeleteCascadeShareObjects:

    def test_one_version(self):
        cw = factories.AbstractCreativeWorkFactory(title='All About Cats')

        assert models.CreativeWork.objects.all().count() == 1
        assert models.AbstractCreativeWorkVersion.objects.count() == 1

        cw.delete()

        assert models.CreativeWork.objects.all().count() == 0
        assert models.AbstractCreativeWorkVersion.objects.count() == 0

    def test_many_versions(self):
        cw = factories.AbstractCreativeWorkFactory(title='All about cats')
        cw.administrative_change(title='All About Kets')

        assert models.CreativeWork.objects.all().count() == 1
        assert models.AbstractCreativeWorkVersion.objects.count() == 2

        assert cw.versions.count() == 2

        cw.delete()

        assert models.CreativeWork.objects.all().count() == 0
        assert models.AbstractCreativeWorkVersion.objects.count() == 0

    def test_multiple_sources(self):
        pass

    def test_no_truncate(self):
        cws = [factories.AbstractCreativeWorkFactory() for _ in range(10)]

        assert models.CreativeWork.objects.all().count() == 10
        assert models.AbstractCreativeWorkVersion.objects.count() == 10

        for i, cw in enumerate(cws):
            cw.delete()
            assert models.CreativeWork.objects.all().count() == 9 - i
            assert models.AbstractCreativeWorkVersion.objects.count() == 9 - i


@pytest.mark.django_db
class TestDeleteCascadeRelations:

    def test_foreign_key(self):
        identifier = factories.WorkIdentifierFactory()

        assert models.WorkIdentifier.objects.count() == 1
        assert models.AbstractCreativeWork.objects.count() == 1
        assert models.WorkIdentifierVersion.objects.count() == 1
        assert models.AbstractCreativeWorkVersion.objects.count() == 1

        identifier.delete()

        assert models.WorkIdentifier.objects.count() == 0
        assert models.AbstractCreativeWork.objects.count() == 1
        assert models.WorkIdentifierVersion.objects.count() == 0
        assert models.AbstractCreativeWorkVersion.objects.count() == 1

    def test_foreign_key_inverse(self):
        identifier = factories.WorkIdentifierFactory()

        assert models.WorkIdentifier.objects.count() == 1
        assert models.AbstractCreativeWork.objects.count() == 1
        assert models.WorkIdentifierVersion.objects.count() == 1
        assert models.AbstractCreativeWorkVersion.objects.count() == 1

        identifier.creative_work.delete()

        assert models.WorkIdentifier.objects.count() == 0
        assert models.AbstractCreativeWork.objects.count() == 0
        assert models.WorkIdentifierVersion.objects.count() == 0
        assert models.AbstractCreativeWorkVersion.objects.count() == 0

    def test_many_to_many(self):
        work = factories.AbstractCreativeWorkFactory()
        for i in range(10):
            factories.ThroughTagsFactory(creative_work=work, tag=factories.TagFactory(name=str(i)))

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (1, 1),
            models.ThroughTags: (10, 10),
            models.Tag: (10, 10),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

        work.delete()

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (0, 0),
            models.ThroughTags: (0, 0),
            models.Tag: (10, 10),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

    def test_many_to_many_inverse(self):
        for i in range(10):
            factories.ThroughTagsFactory(tag=factories.TagFactory(name=str(i)))

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (10, 10),
            models.ThroughTags: (10, 10),
            models.Tag: (10, 10),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

        models.ThroughTags.objects.all().delete()

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (10, 10),
            models.ThroughTags: (0, 0),
            models.Tag: (10, 10),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

    def test_one_to_one(self):
        work = factories.AbstractCreativeWorkFactory(extra=factories.ExtraDataFactory())

        assert work.extra is not None
        assert work.extra_version is not None

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (1, 1),
            models.ExtraData: (1, 1),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

        work.delete()

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (0, 0),
            models.ExtraData: (1, 1),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

    def test_one_to_one_inverse(self):
        work = factories.AbstractCreativeWorkFactory(extra=factories.ExtraDataFactory())

        assert work.extra is not None
        assert work.extra_version is not None

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (1, 1),
            models.ExtraData: (1, 1),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count

        work.extra.delete()

        for model, (count, version_count) in {
            models.AbstractCreativeWork: (0, 0),
            models.ExtraData: (0, 0),
        }.items():
            assert model.objects.count() == count
            assert model.VersionModel.objects.count() == version_count


@pytest.mark.django_db
class TestDeleteCascadeNonShareObjects:

    def test_change(self):
        work = factories.AbstractCreativeWorkFactory()
        work.change.delete()

        assert models.AbstractCreativeWork.objects.count() == 0

    def test_changeset(self):
        work = factories.AbstractCreativeWorkFactory()
        work.change.change_set.delete()

        assert models.Change.objects.count() == 0
        assert models.AbstractCreativeWork.objects.count() == 0

    def test_normalizeddata(self):
        work = factories.AbstractCreativeWorkFactory()
        work.change.change_set.normalized_data.delete()

        assert models.Change.objects.count() == 0
        assert models.ChangeSet.objects.count() == 0
        assert models.AbstractCreativeWork.objects.count() == 0

    def test_rawdata(self, source_config):
        work = factories.AbstractCreativeWorkFactory(change__change_set__normalized_data__raw=models.RawDatum.objects.store_data(source_config, FetchResult('unique', 'data')))
        work.change.change_set.normalized_data.delete()

        assert models.Change.objects.count() == 0
        assert models.ChangeSet.objects.count() == 0
        assert models.NormalizedData.objects.count() == 0
        assert models.AbstractCreativeWork.objects.count() == 0


@pytest.mark.django_db
class TestDeleteCascade:
    initial = [
        Preprint(
            tags=[Tag(name=' Science')],
            identifiers=[WorkIdentifier(1)],
            related_agents=[
                Person(),
                Person(),
                Person(),
                Institution(),
            ],
            related_works=[
                Article(tags=[Tag(name='Science\n; Stuff')], identifiers=[WorkIdentifier(2)])
            ]
        ),
        CreativeWork(
            tags=[Tag(name='Ghosts N Stuff')],
            identifiers=[WorkIdentifier(3)],
            related_agents=[
                Person(),
                Person(),
                Person(),
                Organization(name='Aperture Science'),
                Institution(),
            ],
            related_works=[
                DataSet(identifiers=[WorkIdentifier(4)], related_agents=[Consortium()])
            ]
        ),
        Publication(
            tags=[Tag(name=' Science')],
            identifiers=[WorkIdentifier(5)],
            related_agents=[Organization(name='Umbrella Corporation')],
            related_works=[
                Patent(
                    tags=[Tag(name='Science\n; Stuff')],
                    identifiers=[WorkIdentifier(6)]
                )
            ]
        ),
    ]

    @pytest.mark.parametrize('queryset, deltas', [
        (
            models.NormalizedData.objects.all(), {
                models.AbstractCreativeWork: -6,
                models.AbstractAgent: -11,
                models.ChangeSet: -1,
                models.Change: -47,
            }
        ), (
            models.DataSet.objects.all(), {
                models.DataSet: -1,
                models.AbstractCreativeWork: -1,
                models.Preprint: 0,
                models.Change: 0,
            }
        ), (
            models.ChangeSet.objects.all(), {
                models.Change: -47,
                models.DataSet: -1,
                models.AbstractAgent: -11,
                models.AbstractCreativeWork: -6,
                models.NormalizedData: 0,
            }
        ), (
            models.Tag.objects.filter(name='science'), {
                models.Tag: -1,
                apps.get_model('share.Tag_sources'): -1,
                models.Tag: -1,
                models.Tag.VersionModel: -1,
                models.ThroughTags: -4,
                models.ThroughTags.VersionModel: -4,
                models.ChangeSet: 0,
                models.Change: 0,
                models.AbstractCreativeWork: 0,
                models.AbstractCreativeWork.VersionModel: 0,
            }
        )
    ])
    def test_delete_cascade(self, queryset, deltas, Graph, ingest):
        ingest(Graph(self.initial))

        before = {model: model.objects.count() for model in deltas.keys()}

        queryset.delete()

        for model, delta in deltas.items():
            assert model.objects.count() - before[model] == delta
