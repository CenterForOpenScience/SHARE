import pytest

from share.harvest.base import FetchResult
from share.models import SourceConfig, RawDatum

data = '''
<div id="innertext">
<h1>A. Michael Powell Herbarium (SRSC)</h1> <div style="margin:10px;">
<div>
Sample description
</div>
<div style="margin-top:5px;">
<b>Contact:</b> Test Author (author@email.com)
                                </div>
<div style="margin-top:5px;">
</div>
<div style="margin-top:5px;">
<b>Collection Type: </b>Preserved Specimens
        </div>
<div style="margin-top:5px;">
<b>Management: </b>Data snapshot of local collection database <div style="margin-top:5px;"><b>Last Update:</b> 1 October 2016</div>
</div>
<div style="margin-top:5px;">
<b>Usage Rights:</b> <a href="http://creativecommons.org/licenses/by-nc/3.0/" target="_blank">CC BY-NC (Attribution-Non-Commercial)</a>
</div>
<div style="margin-top:5px;">
<b>Rights Holder:</b> Sul Ross University
        </div>
<div style="clear:both;margin-top:5px;">
<div style="font-weight:bold;">Collection Statistics:</div>
<ul style="margin-top:5px;">
<li>4,868 specimen records</li>
<li>1,195 (25%) georeferenced</li>
<li>2,954 (61%) with images</li><li>2,849 (59%) identified to species</li>
<li>104 families</li>
<li>361 genera</li>
<li>661 species</li>
<li>762 total taxa (including subsp. and var.)</li>
</ul>
</div>
</div>
</div>
'''


@pytest.mark.django_db
def test_swbiodiversity_transformer():
    config = SourceConfig.objects.get(label=('org.swbiodiversity'))
    transformer = config.get_transformer()
    fetch_result = FetchResult('http://swbiodiversity.org/seinet/collections/misc/collprofiles.php?collid=187', data)
    raw_datum = RawDatum.objects.store_data(config, fetch_result)

    graph = transformer.transform(raw_datum)

    dataset = graph.filter_nodes(lambda n: n.type == 'dataset')[0]

    assert dataset.type == 'dataset'
    assert dataset['description'] == 'Sample description'
    assert dataset['title'] == 'A. Michael Powell Herbarium (SRSC)'
    assert dataset['extra']['usage_rights'] == 'CC BY-NC (Attribution-Non-Commercial)'
    assert dataset['extra']['access_rights'] == 'Sul Ross University'
    assert dataset['extra']['collection_statistics'] == {
        "(25%) georeferenced": "1,195",
        "(59%) identified to species": "2,849",
        "(61%) with images": "2,954",
        "families": "104",
        "genera": "361",
        "species": "661",
        "specimen records": "4,868",
        "total taxa (including subsp. and var.)": "762"
    }

    agent_relations = dataset['agent_relations']
    assert len(agent_relations) == 1
    agent = agent_relations[0]['agent']
    assert agent['given_name'] == 'Test'
    assert agent['identifiers'][0]['uri'] == 'mailto:author@email.com'

    identifiers = dataset['identifiers']
    assert len(identifiers) == 1
    assert identifiers[0]['uri'] == 'http://swbiodiversity.org/seinet/collections/misc/collprofiles.php?collid=187'
