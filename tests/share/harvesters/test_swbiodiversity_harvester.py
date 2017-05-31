from datetime import timedelta

import requests_mock
import pendulum
import pytest

from share.models import SourceConfig

main_page = '''
<html>
<head>
    <title>SEINet - Arizona Chapter  Collection Profiles</title>
</head>
<body>
<table>
    <div id="innertext">
            <h1>SEINet - Arizona Chapter Collections </h1>
            <div>
                Select a collection to see full details.
            </div>
            <table style='margin:10px;'>
                    <tr>
                        <td>
                            <h3>
                                <a href='collprofiles.php?collid=223'>
                                    A. Michael Powell Herbarium
                                </a>
                            </h3>
                            <div style='margin:10px;'>
                                <div>Sample description</div>
                                <div style='margin-top:5px;'>
                                    <b>Contact:</b>
                                    Test Author (author@email.com)
                                </div>
                            </div>
                        </td>
                    </tr>
            </table>
    </div>
</table>
</body>
</html>
'''

collection_page = '''
<html>
<head>
    <title>SEINet - Arizona Chapter A. Michael Powell Herbarium Collection Profiles</title
</head>
<body>
<table>
<!-- This is inner text! -->
    <div id="innertext">
        <h1>A. Michael Powell Herbarium (SRSC)</h1>			<div style='margin:10px;'>
                <div>
                Sample description
                </div>
                <div style='margin-top:5px;'>
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
                </td>
    </tr>
</table>
</body>
</html>
'''


@pytest.mark.django_db
def test_func():
    config = SourceConfig.objects.get(label=('org.swbiodiversity'))
    url = config.harvester_kwargs['list_url']
    harvester = config.get_harvester()

    with requests_mock.mock() as m:
        m.get(url, text=main_page)
        m.get(url + '?collid=223', text=collection_page)
        start = pendulum.utcnow() - timedelta(days=3)
        end = pendulum.utcnow()
        result = harvester.do_harvest(start, end)
        for data in result:
            assert data[0] == '223'
            assert data[1]['access-rights'] == 'Sul Ross University'
            assert data[1]['collection-type'] == 'Preserved Specimens'
            assert data[1]['title'] == 'A. Michael Powell Herbarium (SRSC)'
            assert data[1]['description'] == 'Sample description'
            assert data[1]['usage-rights'] == 'CC BY-NC (Attribution-Non-Commercial)'
            assert data[1]['contact']['name'] == 'Test Author'
            assert data[1]['contact']['email'] == 'author@email.com'
            assert data[1]['collection-statistics'] == {
                "(25%) georeferenced": "1,195",
                "(59%) identified to species": "2,849",
                "(61%) with images": "2,954",
                "families": "104",
                "genera": "361",
                "species": "661",
                "specimen records": "4,868",
                "total taxa (including subsp. and var.)": "762"
            }
