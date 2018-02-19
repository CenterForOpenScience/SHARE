import pytest

from share.models import SourceConfig

data = r'''
{
    "record": [
        "OpenTeQ - Opening the black box of Teacher Quality",
        "https://www.socialscienceregistry.org/trials/1638",
        "June 06, 2017",
        "2017-06-06 11:59:10 -0400",
        "2017-06-06",
        "AEARCTR-0001638",
        "Daniel Adam, dan@gmail.com",
        "on_going",
        "2016-03-01",
        "2018-09-22",
        "[\"education\", \"\"]",
        "",
        "test description",
        "2016-10-20",
        "2017-07-15",
        "demo text",
        "description",
        "plan",
        "",
        "Randomization done in office by a computer, by a researcher external to the project staff (Giovanni Abbiati - IRVAPP, abbiati@irvapp.it",
        "schools (whithin blocks)",
        "198 schools whithin 8 blocks",
        "around 2.200 teachers teaching Math or Italian to 7th gradersaround 24.000 students for each grade (6th, 7th, 8th)",
        "50 schools individual treatment50 schools collective treatment98 schools control",
        "demo text",
        "Private",
        "This section is unavailable to the public.",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "This section is unavailable to the public. Use the button below to request access to this information.",
        "",
        "",
        "",
        "",
        "",
        ""
    ]
}
'''


@pytest.mark.django_db
def test_AEA_transformer():
    config = SourceConfig.objects.get(label='org.socialscienceregistry')
    transformer = config.get_transformer()
    graph = transformer.transform(data)
    registration = graph.filter_nodes(lambda n: n.type == 'registration')[0]

    assert registration.type == 'registration'
    assert registration['description'] == 'test description'
    assert registration['title'] == 'OpenTeQ - Opening the black box of Teacher Quality'
    assert registration['extra']['primary_investigator'] == {'email': 'dan@gmail.com', 'name': 'Daniel Adam'}
    assert registration['extra']['interventions'] == {'end-date': '2017-07-15', 'start-date': '2016-10-20'}
