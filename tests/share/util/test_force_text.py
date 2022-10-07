import pytest
from share.legacy_normalize.transform.chain.utils import force_text


@pytest.mark.parametrize('input_text, output_text', [
    (['architecture', 'art', 'mechanical'], ['architecture', 'art', 'mechanical']),
    (['architecture', {'#text': 'art'}, 'mechanical'], ['architecture', 'art', 'mechanical']),
    (['architecture', {'#text': 'art'}, None], ['architecture', 'art']),
    ([None, {'#text': 'art'}, None], ['art']),
    ({'#text': 'art'}, 'art'),
    ('mechanical', 'mechanical'),
    (None, ''),
    ({}, ''),
    ({'test': 'value'}, '')
])
def test_force_text(input_text, output_text):
    assert force_text(input_text) == output_text


@pytest.mark.parametrize('input_text, list_sep, output_text', [
    (['architecture', 'art', 'mechanical'], None, ['architecture', 'art', 'mechanical']),
    (['architecture', 'art', 'mechanical'], '\n', 'architecture\nart\nmechanical'),
    (['architecture', 'art', 'mechanical'], ' word ', 'architecture word art word mechanical'),
    (['architecture', {'#text': 'art'}, 'mechanical'], '\n', 'architecture\nart\nmechanical'),
    (['architecture', {'#text': 'art'}, None], ' f', 'architecture fart'),
    ([None, {'#text': 'art'}, None], '|', 'art'),
    ({'#text': 'art'}, ' word ', 'art'),
    ('mechanical', 'foo', 'mechanical'),
    (None, '\n', ''),
])
def test_force_text_joined(input_text, list_sep, output_text):
    assert force_text(input_text, list_sep) == output_text
