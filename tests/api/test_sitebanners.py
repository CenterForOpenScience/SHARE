import pytest

from share.models import SiteBanner
from share.util import IDObfuscator
from tests.factories import ShareUserFactory


@pytest.mark.django_db
class TestSiteBanners:

    def test_list(self, client):
        resp = client.get('/api/v2/site_banners/')
        assert resp.status_code == 200
        assert resp.json() == {
            'data': [],
            'links': {
                'first': 'http://testserver/api/v2/site_banners/?page=1',
                'last': 'http://testserver/api/v2/site_banners/?page=1',
                'next': None,
                'prev': None,
            },
            'meta': {
                'pagination': {'count': 0, 'pages': 1, 'page': 1},
            }
        }

    def test_list_with_items(self, client):
        user = ShareUserFactory()
        banner = SiteBanner.objects.create(
            title='Why wasnt I there',
            description='I could have saved them',
            created_by=user,
            last_modified_by=user,
        )
        resp = client.get('/api/v2/site_banners/')
        assert resp.status_code == 200
        assert resp.json() == {
            'data': [{
                'id': IDObfuscator.encode(banner),
                'type': 'SiteBanner',
                'attributes': {
                    'color': 'info',
                    'icon': 'exclamation',
                    'title': 'Why wasnt I there',
                    'description': 'I could have saved them',
                }
            }],
            'links': {
                'first': 'http://testserver/api/v2/site_banners/?page=1',
                'last': 'http://testserver/api/v2/site_banners/?page=1',
                'next': None,
                'prev': None,
            },
            'meta': {
                'pagination': {'count': 1, 'pages': 1, 'page': 1},
            }
        }

    # def test_get_item(self, client):
    #     resp = client.get('/api/v2/site_banners/')
    #     assert resp.status_code == 200
    #     assert resp.json() == {
    #         'data': [],
    #         'meta': {
    #         }
    #     }
