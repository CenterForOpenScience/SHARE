import pytest
from share.transform.chain.utils import force_text


@pytest.mark.parametrize('input_text, output_text', [
    (['architecture', 'art', 'mechanical'], ['architecture', 'art', 'mechanical']),
    (['architecture', {'#text': 'art'}, 'mechanical'], ['architecture', 'art', 'mechanical']),
    (['architecture', {'#text': 'art'}, None], ['architecture', 'art']),
    ([None, {'#text': 'art'}, None], ['art']),
    ({'#text': 'art'}, 'art'),
    ('mechanical', 'mechanical'),
    (None, ''),
])
def test_force_text(input_text, output_text):
    assert force_text(input_text) == output_text
