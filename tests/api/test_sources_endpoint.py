import json
import pytest

from share.models import Source, ShareUser


PROPER_ICON_URL = 'https://staging-cdn.osf.io/preprints-assets/bitss/square_color_no_transparent.png'
IMPROPER_ICON_URL = 'https://github.com/CenterForOpenScience/SHARE.git'
INVALID_URL = 'invalidURL'


def get_test_data(icon=PROPER_ICON_URL, home_page=None):
    test_data = {
        'data': {
            'type': 'Sources',
            'attributes': {
                'long_title': 'Test User',
                'icon': icon,
                'home_page': home_page
            }
        }
    }
    return test_data


@pytest.mark.django_db
class TestSourcesGet:
    endpoint = '/api/v2/sources/'

    def test_count(self, client):
        total = Source.objects.exclude(icon='').exclude(is_deleted=True).count()

        resp = client.get(self.endpoint)

        assert total > 0
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == total

    def test_is_deleted(self, client):
        total = Source.objects.exclude(icon='').exclude(is_deleted=True).count()

        s = Source.objects.first()
        s.is_deleted = True
        s.save()

        resp = client.get(self.endpoint)
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == total - 1

    def test_no_icon(self, client):
        total = Source.objects.exclude(icon='').exclude(is_deleted=True).count()

        s = Source.objects.first()
        s.icon = None
        s.save()

        resp = client.get(self.endpoint)
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == total - 1


@pytest.mark.django_db
class TestSourcesPost:
    endpoint = '/api/v2/sources/'

    def test_unauthorized_post(self, client):
        assert client.post(
            self.endpoint,
            json.dumps(get_test_data()),
            content_type='application/vnd.api+json'
        ).status_code == 401

    def test_improper_scope_post(self, client, share_user):
        assert client.post(
            self.endpoint,
            json.dumps(get_test_data()),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=share_user.authorization(),
        ).status_code == 403

    def test_successful_post_no_home_page(self, client, source_add_user):
        test_data = get_test_data()
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )
        resp_attributes = resp.data['attributes']
        resp_related_share_user = resp.data['relationships']['share_user']['data']
        resp_related_source_config = resp.data['relationships']['source_config']['data']['attributes']

        created_label = resp_attributes['long_title'].replace(' ', '_').lower()
        created_user = ShareUser.objects.get(pk=resp_related_share_user['id'])

        assert resp.status_code == 201
        assert resp_attributes['long_title'] == test_data['data']['attributes']['long_title']
        assert resp_attributes['name'] == created_label
        assert resp_attributes['home_page'] is None
        assert resp_related_share_user['attributes']['username'] == created_label
        assert resp_related_share_user['attributes']['authorization_token'] == created_user.accesstoken_set.first().token
        assert created_user.is_trusted is True
        assert resp_related_source_config['label'] == created_label

    def test_successful_post_home_page(self, client, source_add_user):
        test_data = get_test_data(home_page='http://test.homepage.net')
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )
        resp_attributes = resp.data['attributes']

        assert resp.status_code == 201
        assert resp_attributes['long_title'] == test_data['data']['attributes']['long_title']
        assert resp_attributes['home_page'] == test_data['data']['attributes']['home_page']

    def test_bad_image_url(self, client, source_add_user):
        test_data = get_test_data(icon=IMPROPER_ICON_URL)
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.status_code == 400
        assert resp.data[0]['detail'] == 'Could not download/process image. ["Invalid type. Expected one of (\'image/png\', \'image/jpeg\'). Received text/html"]'

    def test_invalid_url(self, client, source_add_user):
        test_data = get_test_data(icon=INVALID_URL)
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.status_code == 400
        assert resp.data[0]['detail'] == 'Could not download/process image. Invalid URL \'invalidURL\': No schema supplied. Perhaps you meant http://invalidURL?'
