from datetime import timedelta

from furl import furl
from httpretty import httpretty, httprettified
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
        <h1>A. Michael Powell Herbarium (SRSC)</h1>
        <div style='margin:10px;'>
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
</table>
</body>
</html>
'''


@pytest.mark.django_db
@httprettified
def test_swbiodiversity_harvester():
    httpretty.enable()
    httpretty.allow_net_connect = False

    config = SourceConfig.objects.get(label=('org.swbiodiversity'))
    url = config.harvester_kwargs['list_url']
    harvester = config.get_harvester()

    httpretty.register_uri(httpretty.GET, url,
                           body=main_page, content_type='text/html', match_querystring=True)
    collection = furl(url)
    collection.args['collid'] = 223
    httpretty.register_uri(httpretty.GET, url + ';collid=(\d+)',
                           body=collection_page, content_type='text/html', match_querystring=True)
    start = pendulum.utcnow() - timedelta(days=3)
    end = pendulum.utcnow()
    results = harvester.fetch_date_range(start, end)
    for result in results:
        assert result.identifier == collection.url
        assert "".join(result.datum.split()) == "".join('''
            <div id="innertext">
            <h1>SEINet - Arizona Chapter Collections </h1>
            <div>
                Select a collection to see full details.
            </div>
            <table style="margin:10px;">
            <tr>
            <td>
            <h3>
            <a href="collprofiles.php?collid=223">
                A. Michael Powell Herbarium
            </a>
            </h3>
            <div style="margin:10px;">
            <div>Sample description</div>
            <div style="margin-top:5px;">
            <b>Contact:</b>
               Test Author (author@email.com)
            </div>
            </div>
            </td>
            </tr>
            </table>
            </div>
            '''"".split())

    httpretty.disable()
