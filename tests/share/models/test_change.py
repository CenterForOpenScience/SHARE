import pytest

from share.models import Tag
from share.models import Person
from share.models import AbstractCreativeWork
from share.models import Contributor
from share.models.change import Change
from share.models.change import ChangeSet


@pytest.fixture
def ld_graph():
    return {
        '@context': {},
        '@graph': [
            {'@id': '_:d486fd737bea4fbe9566b7a2842651ef', '@type': 'Organization', 'name': 'Department of Physics'},
            {'@id': '_:c4f10e02785a4b4d878f48d08ffc7fce', 'entity': {'@type': 'Organization', '@id': '_:d486fd737bea4fbe9566b7a2842651ef'}, '@type': 'Affiliation', 'person': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},
            {'@id': '_:7e742fa3377e4f119e36f8629144a0bc', 'affiliations': [{'@type': 'Affiliation', '@id': '_:c4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Prendergast', 'given_name': 'David'},
            {'@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a', '@type': 'Contributor', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'person': {'@type': 'Person', '@id': '_:7e742fa3377e4f119e36f8629144a0bc'}},
            {'@id': '_:69e859cefed140bd9b717c5b610d300c', '@type': 'Organization', 'name': 'NMRC, University College, Cork, Ireland'},
            {'@id': '_:2fd829eeda214adca2d4d34d02b10328', 'entity': {'@type': 'Organization', '@id': '_:69e859cefed140bd9b717c5b610d300c'}, '@type': 'Affiliation', 'person': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},
            {'@id': '_:ed3cc2a50f6d499db933a28d16bca5d6', 'affiliations': [{'@type': 'Affiliation', '@id': '_:2fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Nolan', 'given_name': 'M.'},
            {'@id': '_:27961f3c7c644101a500772477aff304', '@type': 'Contributor', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'person': {'@type': 'Person', '@id': '_:ed3cc2a50f6d499db933a28d16bca5d6'}},
            {'@id': '_:9a1386475d314b9bb524931e24361aaa', 'affiliations': [{'@type': 'Affiliation', '@id': '_:c4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Filippi', 'given_name': 'Claudia'},
            {'@id': '_:bf7726af4542405888463c796e5b7686', '@type': 'Contributor', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'person': {'@type': 'Person', '@id': '_:9a1386475d314b9bb524931e24361aaa'}},
            {'@id': '_:78639db07e2e4ee88b422a8920d8a095', 'affiliations': [{'@type': 'Affiliation', '@id': '_:c4f10e02785a4b4d878f48d08ffc7fce'}], '@type': 'Person', 'family_name': 'Fahy', 'given_name': 'Stephen'},
            {'@id': '_:18d151204d7c431388a7e516defab1bc', '@type': 'Contributor', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'person': {'@type': 'Person', '@id': '_:78639db07e2e4ee88b422a8920d8a095'}},
            {'@id': '_:f4cec0271c7d4085bac26dbb2b32a002', 'affiliations': [{'@type': 'Affiliation', '@id': '_:2fd829eeda214adca2d4d34d02b10328'}], '@type': 'Person', 'family_name': 'Greer', 'given_name': 'J.'},
            {'@id': '_:a17f28109536459ca02d99bf777400ae', '@type': 'Contributor', 'creative_work': {'@type': 'Article', '@id': '_:6203fec461bb4b3fa956772acbd9c50d'}, 'person': {'@type': 'Person', '@id': '_:f4cec0271c7d4085bac26dbb2b32a002'}},
            {'@id': '_:6203fec461bb4b3fa956772acbd9c50d', 'contributors': [{'@type': 'Contributor', '@id': '_:687a4ba2cbd54ab7a2f2c3cd1777ea8a'}, {'@type': 'Contributor', '@id': '_:27961f3c7c644101a500772477aff304'}, {'@type': 'Contributor', '@id': '_:bf7726af4542405888463c796e5b7686'}, {'@type': 'Contributor', '@id': '_:18d151204d7c431388a7e516defab1bc'}, {'@type': 'Contributor', '@id': '_:a17f28109536459ca02d99bf777400ae'}], 'title': 'Impact of Electron-Electron Cusp on Configuration Interaction Energies', '@type': 'Article', 'description': '  The effect of the electron-electron cusp on the convergence of configuration\ninteraction (CI) wave functions is examined. By analogy with the\npseudopotential approach for electron-ion interactions, an effective\nelectron-electron interaction is developed which closely reproduces the\nscattering of the Coulomb interaction but is smooth and finite at zero\nelectron-electron separation. The exact many-electron wave function for this\nsmooth effective interaction has no cusp at zero electron-electron separation.\nWe perform CI and quantum Monte Carlo calculations for He and Be atoms, both\nwith the Coulomb electron-electron interaction and with the smooth effective\nelectron-electron interaction. We find that convergence of the CI expansion of\nthe wave function for the smooth electron-electron interaction is not\nsignificantly improved compared with that for the divergent Coulomb interaction\nfor energy differences on the order of 1 mHartree. This shows that, contrary to\npopular belief, description of the electron-electron cusp is not a limiting\nfactor, to within chemical accuracy, for CI calculations.\n'}  # noqa
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
        identifier, preprint, _ = change_factory.from_graph({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'identifier',
                'url': 'https://share.osf.io',
            }, {
                '@id': '_:5678',
                '@type': 'WorkIdentifier',
                'identifier': {'@id': '_:1234', '@type': 'identifier'},
                'creative_work': {'@id': '_:890', '@type': 'preprint'},
            }, {
                '@id': '_:890',
                '@type': 'preprint',
                'title': 'All about Cats and more',
                'identifiers': [{'@id': '_:5678', '@type': 'WorkIdentifier'}]
            }]
        }).accept()

        change_set = change_factory.from_graph({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'identifier',
                'url': 'https://share.osf.io',
            }, {
                '@id': '_:5678',
                '@type': 'workidentifier',
                'identifier': {'@id': '_:1234', '@type': 'identifier'},
                'creative_work': {'@id': '_:890', '@type': 'preprint'},
            }, {
                '@id': '_:890',
                '@type': 'preprint',
                'title': 'JUST ABOUT CATS',
                'identifiers': [{'@id': '_:5678', '@type': 'workidentifier'}],
            }]
        }, disambiguate=True)

        assert change_set.changes.count() == 1
        assert change_set.changes.first().target == preprint

    # def test_update_requires_saved(self, share_source):
    #     p = Person(given_name='John', family_name='Doe', source=share_source)

    #     with pytest.raises(AssertionError):
    #         ChangeRequest.objects.update_object(p, share_source)

    # def test_create_requires_unsaved(self, share_source):
    #     change = ChangeRequest.objects.create_object(
    #         Person(given_name='John', family_name='Doe', source=share_source),
    #         share_source
    #     )
    #     change.save()
    #     p = change.accept()

    #     with pytest.raises(AssertionError):
    #         ChangeRequest.objects.create_object(p, share_source)

    # def test_requirements(self, share_source):
    #     p = Person(given_name='Jane', family_name='Doe', source=share_source)
    #     p_change = ChangeRequest.objects.create_object(p, share_source)

    #     e = Email(email='example@example.com', source=share_source)
    #     e_change = ChangeRequest.objects.create_object(e, share_source)

    #     pe = PersonEmail(email=e, person=p, source=share_source)

    #     change = ChangeRequest.objects.create_object(pe, share_source)

    #     assert change.depends_on.count() == 2

    #     expected = {
    #         'email_id': e_change,
    #         'person_id': p_change,
    #     }

    #     for req in change.depends_on.all():
    #         assert req.change == change
    #         assert req.requirement == expected[req.field]

    # def test_requirements_must_be_accepted(self, share_source):
    #     p = Person(given_name='Jane', family_name='Doe', source=share_source)
    #     ChangeRequest.objects.create_object(p, share_source)

    #     e = Email(email='example@example.com', source=share_source)
    #     ChangeRequest.objects.create_object(e, share_source)

    #     pe = PersonEmail(email=e, person=p, source=share_source)

    #     change = ChangeRequest.objects.create_object(pe, share_source)

    #     with pytest.raises(AssertionError) as e:
    #         change.accept()

    #     assert e.value.args[0] == 'Not all dependancies have been accepted'

    # def test_accept_requirements(self, share_source):
    #     p = Person(given_name='Jane', family_name='Doe', source=share_source)
    #     ChangeRequest.objects.create_object(p, share_source).accept()

    #     e = Email(email='example@example.com', is_primary=False, source=share_source)
    #     ChangeRequest.objects.create_object(e, share_source).accept()

    #     change = ChangeRequest.objects.create_object(
    #         PersonEmail(email=e, person=p, source=share_source),
    #         share_source
    #     )
    #     pe = change.accept()

    #     pe.refresh_from_db()

    #     assert pe.change == change
    #     assert pe.person.given_name == 'Jane'
    #     assert pe.person.family_name == 'Doe'
    #     assert pe.email.email == 'example@example.com'

    # def test_mixed_requirements(self, share_source):
    #     p = ChangeRequest.objects.create_object(
    #         Person(given_name='Jane', family_name='Doe', source=share_source),
    #         share_source
    #     ).accept()

    #     e = Email(email='example@example.com', is_primary=False, source=share_source)
    #     e_change = ChangeRequest.objects.create_object(e, share_source)

    #     change = ChangeRequest.objects.create_object(
    #         PersonEmail(email=e, person=p, source=share_source),
    #         share_source
    #     )

    #     assert change.depends_on.count() == 1
    #     assert change.depends_on.first().requirement == e_change

    # def test_recurse(self, share_source):
    #     p = Person(given_name='Jane', family_name='Doe', source=share_source)
    #     ChangeRequest.objects.create_object(p, share_source)

    #     e = Email(email='example@example.com', is_primary=True, source=share_source)
    #     ChangeRequest.objects.create_object(e, share_source)

    #     pe = PersonEmail(email=e, person=p, source=share_source)
    #     change = ChangeRequest.objects.create_object(pe, share_source)

    #     pe = change.accept(recurse=True)

    #     pe.refresh_from_db()

    #     assert pe.person.given_name == 'Jane'
    #     assert pe.email.email == 'example@example.com'


@pytest.mark.django_db
class TestChangeGraph:

    def test_changes(self, change_factory, ld_graph):
        change_factory.from_graph(ld_graph).accept()

        assert Person.objects.filter(pk__isnull=False).count() == 5
        assert Contributor.objects.filter(pk__isnull=False).count() == 5
        assert AbstractCreativeWork.objects.filter(pk__isnull=False).count() == 1

    def test_change_existing(self, change_factory, jane_doe):
        change_set = change_factory.from_graph({
            '@graph': [{
                '@id': jane_doe.pk,
                '@type': 'Person',
                'given_name': 'John'
            }]
        }, disambiguate=True)

        assert change_set.changes.first().target == jane_doe

        assert jane_doe.given_name == 'Jane'

        change_set.accept()
        jane_doe.refresh_from_db()

        assert jane_doe.given_name == 'John'

    def test_handles_unique_violation(self, change_factory, change_ids):
        tag = Tag.objects.create(name='MyCoolTag', change_id=change_ids.get())

        change_set = change_factory.from_graph({
            '@graph': [{
                '@type': 'Tag',
                '@id': '_:1234',
                'name': 'MyCoolTag'
            }]
        })

        assert change_set.accept()[0] == tag
