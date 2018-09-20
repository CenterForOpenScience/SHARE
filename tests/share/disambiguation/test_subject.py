import pytest

from share import models

import tests.share.normalize.factories as f


initial = [
    f.Subject(name='Science!', uri='http://science.io'),
    f.Subject(name='Art!', uri='http://art.io'),
]


@pytest.mark.django_db
class TestSubject:

    @pytest.fixture
    def ingest_initial(self, Graph, ingest, system_user):
        ingest(Graph(initial), user=system_user)

    @pytest.mark.parametrize('input, model_deltas', [
        ([f.Subject(name='Science!')], {
            models.Subject: 0,
            models.SubjectTaxonomy: 0,
        }),
        ([f.Publication(subjects=[f.Subject(name='Science!')])], {
            models.Publication: 1,
            models.Subject: 0,
            models.ThroughSubjects: 1,
            models.SubjectTaxonomy: 0,
        }),
        ([f.Publication(subjects=[f.Subject(
            name='Science synonym!',
            central_synonym=f.Subject(name='Science!')
        )])], {
            models.Publication: 1,
            models.Subject: 1,
            models.ThroughSubjects: 1,
            models.SubjectTaxonomy: 1,
        }),
    ])
    def test_disambiguate(self, input, model_deltas, Graph, ingest_initial, ingest):
        # Nasty hack to avoid progres' fuzzy counting
        before = {
            m: m.objects.exclude(id=None).count()
            for m in model_deltas.keys()
        }

        ingest(Graph(input))

        after = {
            m: m.objects.exclude(id=None).count()
            for m in model_deltas.keys()
        }

        for model, delta in model_deltas.items():
            assert after[model] - before[model] == delta

    @pytest.mark.parametrize('input', [
        (f.Subject(name='Not Science!', uri='http://science.io')),
        (f.Subject(name='Science!')),
    ])
    def test_protect_central_taxonomy(self, input, Graph, ingest_initial, ingest):
        cs = ingest(Graph(input))
        assert cs is None

    def test_no_changes(self, Graph, ingest_initial, ingest):
        cs = ingest(Graph(initial))
        assert cs is None
