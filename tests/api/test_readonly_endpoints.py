import json
import pytest


def get_test_data(endpoint_type):
    test_data = {
        'data': {
            'type': endpoint_type,
            'attributes': {
                'data': {
                    '@graph': [{
                        '@type': 'Person',
                        'given_name': 'Jim',
                    }]
                }
            }
        }
    }
    return test_data


@pytest.mark.django_db
class TestRawDataEndpoint:
    endpoint = '/api/v2/rawdata/'

    def test_status(self, client):
        assert client.get(self.endpoint).status_code == 200

    def test_post(self, client, trusted_user):
        assert client.post(
            self.endpoint,
            json.dumps(get_test_data('RawData')),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token,
        ).status_code == 405


@pytest.mark.django_db
class TestSourcesEndpoint:
    endpoint = '/api/v2/sources/'

    def test_status(self, client):
        assert client.get(self.endpoint).status_code == 200

    def test_post(self, client, trusted_user):
        assert client.post(
            self.endpoint,
            json.dumps(get_test_data('Source')),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token,
        ).status_code == 405


@pytest.mark.django_db
class TestSiteBannersEndpoint:
    endpoint = '/api/v2/site_banners/'

    def test_status(self, client):
        assert client.get(self.endpoint).status_code == 200

    def test_post(self, client, trusted_user):
        assert client.post(
            self.endpoint,
            json.dumps(get_test_data('SiteBanner')),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token,
        ).status_code == 405
