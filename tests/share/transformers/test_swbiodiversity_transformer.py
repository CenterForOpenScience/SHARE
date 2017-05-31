import pytest

from share.models import SourceConfig

data = '''
{
    "access-rights": "Sul Ross University",
    "collection-statistics": {
        "(25%) georeferenced": "1,195",
        "(59%) identified to species": "2,849",
        "(61%) with images": "2,954",
        "families": "104",
        "genera": "361",
        "species": "661",
        "specimen records": "4,868",
        "total taxa (including subsp. and var.)": "762"
    },
    "collection_type": "Preserved Specimens",
    "contact": {
        "email": "ampowell@sulross.edu",
        "name": "A. Michael Powell"
    },
    "description": "test description",
    "identifier": "223",
    "management": "Data snapshot of local collection database Last Update: 1 October 2016",
    "title": "A. Michael Powell Herbarium (SRSC)",
    "usage-rights": "CC BY-NC (Attribution-Non-Commercial)"
}
'''


@pytest.mark.django_db
def test_func():
    config = SourceConfig.objects.get(label=('org.swbiodiversity'))
    transformer = config.get_transformer()
    result = transformer.transform(data)

    assert result['@graph'][3]['@type'] == 'dataset'
    assert result['@graph'][3]['description'] == 'test description'
    assert result['@graph'][3]['title'] == 'A. Michael Powell Herbarium (SRSC)'
    assert result['@graph'][3]['extra']['usage_rights'] == 'CC BY-NC (Attribution-Non-Commercial)'
    assert result['@graph'][3]['extra']['access_rights'] == 'Sul Ross University'
    assert result['@graph'][3]['extra']['identifiers'] == '223'
    assert result['@graph'][3]['extra']['collection_statistics'] == {
        "(25%) georeferenced": "1,195",
        "(59%) identified to species": "2,849",
        "(61%) with images": "2,954",
        "families": "104",
        "genera": "361",
        "species": "661",
        "specimen records": "4,868",
        "total taxa (including subsp. and var.)": "762"
    }
