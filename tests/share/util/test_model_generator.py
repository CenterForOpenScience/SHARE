import pytest

from django.apps import apps


@pytest.mark.parametrize('model_name, field_name', [
    ('Funder', 'awards'),
    ('Funder', 'award_versions'),
    ('Funder', 'agent'),
    ('Funder', 'creative_work'),
    ('Contributor', 'contributed_through'),
    ('Creator', 'order_cited'),
    ('Person', 'given_name'),
    ('Person', 'family_name'),
    ('Person', 'additional_name'),
    ('Person', 'suffix'),
])
def test_field_exists(model_name, field_name):
    model = apps.get_model('share', model_name)
    field = model._meta.get_field(field_name)
    assert field
