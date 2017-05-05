import pytest
import pendulum

from django.db import IntegrityError

from share.models import AbstractCreativeWork
from share.models import AgentWorkRelation
from share.models import NormalizedData
from share.models import Person
from share.models import Tag
from share.models.change import Change
from share.models.change import ChangeSet
from share import tasks
from share.util import IDObfuscator

from tests import factories


@pytest.fixture
def ld_graph():
    return {
        '@context': {},
        '@graph': [
            {'@id': '_:d486fd737bea4fbe9566b7a2842651ef', '@type': 'Organization', 'name': 'Department of Physics'},

            {'@id': '_:c4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': '_:d486fd737bea4fbe9566b7a2842651ef'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},
            {'@id': '_:7e742fa3377e4f119e36f8629144a0bc', 'related_agents': [{'@type': 'IsAffiliatedWith', '@id': '_:c4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Prendergast', 'given_name': 'David'},
            {'@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'agent': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},

            {'@id': '_:69e859cefed140bd9b717c5b610d300c', '@type': 'Organization', 'name': 'NMRC, University College, Cork, Ireland'},

            {'@id': '_:2fd829eeda214adca2d4d34d02b10328', 'related': {'@type': 'Organization', '@id': '_:69e859cefed140bd9b717c5b610d300c'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},
            {'@id': '_:ed3cc2a50f6d499db933a28d16bca5d6', 'related_agents': [{'@type': 'IsAffiliatedWith', '@id': '_:2fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Nolan', 'given_name': 'M.'},
            {'@id': '_:27961f3c7c644101a500772477aff304', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'agent': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},

            {'@id': '_:d4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': '_:d486fd737bea4fbe9566b7a2842651ef'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:9a1386475d314b9bb524931e24361aaa'}},
            {'@id': '_:9a1386475d314b9bb524931e24361aaa', 'related_agents': [{'@type': 'IsAffiliatedWith', '@id': '_:d4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Filippi', 'given_name': 'Claudia'},
            {'@id': '_:bf7726af4542405888463c796e5b7686', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'agent': {'@type': 'Person', '@id': '_:9a1386475d314b9bb524931e24361aaa'}},

            {'@id': '_:e4f10e02785a4b4d878f48d08ffc7fce', 'related': {'@type': 'Organization', '@id': '_:d486fd737bea4fbe9566b7a2842651ef'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:78639db07e2e4ee88b422a8920d8a095'}},
            {'@id': '_:78639db07e2e4ee88b422a8920d8a095', 'related_agents': [{'@type': 'IsAffiliatedWith', '@id': '_:e4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Fahy', 'given_name': 'Stephen'},
            {'@id': '_:18d151204d7c431388a7e516defab1bc', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'agent': {'@type': 'Person', '@id': '_:78639db07e2e4ee88b422a8920d8a095'}},

            {'@id': '_:5fd829eeda214adca2d4d34d02b10328', 'related': {'@type': 'Organization', '@id': '_:69e859cefed140bd9b717c5b610d300c'}, '@type': 'IsAffiliatedWith', 'subject': {'@type': 'Person', '@id': '_:f4cec0271c7d4085bac26dbb2b32a002'}},
            {'@id': '_:f4cec0271c7d4085bac26dbb2b32a002', 'related_agents': [{'@type': 'IsAffiliatedWith', '@id': '_:5fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Greer', 'given_name': 'J.'},
            {'@id': '_:a17f28109536459ca02d99bf777400ae', '@type': 'Creator', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'agent': {'@type': 'Person', '@id': '_:f4cec0271c7d4085bac26dbb2b32a002'}},

            {'@id': '_:6203fec461bb4b3fa956772acbd9c50d', 'date_updated': '2016-10-20T00:00:00+00:00', 'related_agents': [{'@type': 'Creator', '@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a'}, {'@type': 'Creator', '@id': '_:27961f3c7c644101a500772477aff304'}, {'@type': 'Creator', '@id': '_:bf7726af4542405888463c796e5b7686'}, {'@type': 'Creator', '@id': '_:18d151204d7c431388a7e516defab1bc'}, {'@type': 'Creator', '@id': '_:a17f28109536459ca02d99bf777400ae'}], 'title': 'Impact of Electron-Electron Cusp on Configuration Interaction Energies', '@type': 'Article', 'description': '  The effect of the electron-electron cusp on the convergence of configuration\ninteraction (CI) wave functions is examined. By analogy with the\npseudopotential approach for electron-ion interactions, an effective\nelectron-electron interaction is developed which closely reproduces the\nscattering of the Coulomb interaction but is smooth and finite at zero\nelectron-electron separation. The exact many-electron wave function for this\nsmooth effective interaction has no cusp at zero electron-electron separation.\nWe perform CI and quantum Monte Carlo calculations for He and Be atoms, both\nwith the Coulomb electron-electron interaction and with the smooth effective\nelectron-electron interaction. We find that convergence of the CI expansion of\nthe wave function for the smooth electron-electron interaction is not\nsignificantly improved compared with that for the divergent Coulomb interaction\nfor energy differences on the order of 1 mHartree. This shows that, contrary to\npopular belief, description of the electron-electron cusp is not a limiting\nfactor, to within chemical accuracy, for CI calculations.\n'}  # noqa
        ]
    }


@pytest.mark.django_db
class TestChange:

    def test_create_person(self, change_factory):
        change_set = change_factory.from_graph({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'Person',
                'given_name': 'John',
                'family_name': 'Doe'
            }]
        })

        assert change_set.status == ChangeSet.STATUS.pending
        assert change_set.changes.count() == 1
        assert change_set.changes.first().type == Change.TYPE.create

        (person, ) = change_set.accept()

        assert person.change == change_set.changes.first()
        assert change_set.status == ChangeSet.STATUS.accepted

    def test_update_creative_work(self, change_factory):
        preprint, identifier = change_factory.from_graph({
            '@graph': [{
                '@id': '_:5678',
                '@type': 'workidentifier',
                'uri': 'http://share.osf.io',
                'creative_work': {'@id': '_:890', '@type': 'preprint'}
            }, {
                '@id': '_:890',
                '@type': 'preprint',
                'title': 'All about Cats and more',
                'identifiers': [{'@id': '_:5678', '@type': 'workidentifier'}]
            }]
        }).accept()

        change_set = change_factory.from_graph({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'workidentifier',
                'uri': 'http://share.osf.io',
                'creative_work': {'@id': '_:890', '@type': 'preprint'}
            }, {
                '@id': '_:890',
                '@type': 'preprint',
                'title': 'JUST ABOUT CATS',
                'identifiers': [{'@id': '_:1234', '@type': 'workidentifier'}],
            }]
        }, disambiguate=True)

        assert change_set.changes.count() == 1
        assert change_set.changes.first().target == preprint


@pytest.mark.django_db
class TestChangeGraph:

    def test_changes(self, change_factory, ld_graph):
        change_factory.from_graph(ld_graph).accept()

        assert Person.objects.filter(pk__isnull=False).count() == 5
        assert AgentWorkRelation.objects.filter(pk__isnull=False).count() == 5
        assert AbstractCreativeWork.objects.filter(pk__isnull=False).count() == 1

    def test_change_existing(self, change_factory, jane_doe):
        change_set = change_factory.from_graph({
            '@graph': [{
                '@id': IDObfuscator.encode(jane_doe),
                '@type': 'Person',
                'given_name': 'John'
            }]
        }, disambiguate=True)

        assert change_set.changes.first().target == jane_doe

        assert jane_doe.given_name == 'Jane'

        change_set.accept()
        jane_doe.refresh_from_db()

        assert jane_doe.given_name == 'John'

    def test_unique_violation_raises(self, change_factory, change_ids):
        Tag.objects.create(name='mycooltag', change_id=change_ids.get())

        change_set = change_factory.from_graph({
            '@graph': [{
                '@type': 'Tag',
                '@id': '_:1234',
                'name': 'MyCoolTag'
            }]
        }, disambiguate=False)

        with pytest.raises(IntegrityError):
            change_set.accept()

    def test_date_updated_update(self, change_ids, change_factory, all_about_anteaters):
        """
        Submitting an identical date as a string should be recognized as no change.
        """
        all_about_anteaters.date_updated = pendulum.now()
        all_about_anteaters.change_id = change_ids.get()
        all_about_anteaters.save()

        change_set = change_factory.from_graph({
            '@graph': [{
                '@type': 'article',
                '@id': IDObfuscator.encode(all_about_anteaters),
                'date_updated': str(all_about_anteaters.date_updated)
            }]
        }, disambiguate=True)

        assert change_set is None

    def test_add_multiple_sources(self):
        source1 = factories.SourceFactory()
        source2 = factories.SourceFactory()

        work = factories.AbstractCreativeWorkFactory(title='All about Canada')
        data = {'@id': IDObfuscator.encode(work), '@type': 'creativework', 'title': 'All aboot Canada'}

        nd1 = NormalizedData.objects.create(source=source1.user, data={'@graph': [data]})
        nd2 = NormalizedData.objects.create(source=source2.user, data={'@graph': [data]})

        assert work.sources.count() == 0

        tasks.disambiguate(nd1.id)

        work.refresh_from_db()
        assert work.title == 'All aboot Canada'
        assert work.sources.count() == 1

        tasks.disambiguate(nd2.id)

        work.refresh_from_db()
        assert work.title == 'All aboot Canada'
        assert work.sources.count() == 2
