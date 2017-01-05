import pytest
import bleach

from project.settings import ALLOWED_TAGS


@pytest.mark.parametrize('raw_html, bleached_html', [
    ('<p class="Something-that-may-or-may-not-exist" style="size: large;">Horribly styled text</p>', 'Horribly styled text'),
    ('<a href="http://MyEvilSite.io/">Click me for puppies</a>', 'Click me for puppies'),
    ('<b>Puppies</b>', '<b>Puppies</b>'),
    ('<i style="size: xxl; color: orange;" class="geocities-i" data-bind="ko: bestCities">GeoCities was best cities</i>', '<i>GeoCities was best cities</i>')
])
def test_bleach(raw_html, bleached_html):
    bleached = bleach.clean(raw_html, strip=True, tags=ALLOWED_TAGS)
    assert bleached == bleached_html
