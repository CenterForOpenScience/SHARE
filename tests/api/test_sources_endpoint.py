import json
import pytest
import time

import httpretty

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from share.models import Source, ShareUser
from share.util import IDObfuscator


PROPER_ICON_URL = 'https://staging-cdn.osf.io/preprints-assets/bitss/square_color_no_transparent.png'
IMPROPER_ICON_URL = 'https://github.com/CenterForOpenScience/SHARE.git'
INVALID_URL = 'invalidURL'
TIMEOUT_URL = 'http://www.timeouturl.com'


def exceptionCallback(request, uri, headers):
        time.sleep(6)
        return (400, headers, uri)


@pytest.fixture
def source_add_user():
    content_type = ContentType.objects.get_for_model(Source)
    permission = Permission.objects.get(content_type=content_type, codename='add_source')

    user = ShareUser(username='trusted_tester', is_trusted=True)
    user.save()
    user.user_permissions.add(permission)
    return user


@pytest.fixture
def mock_icon_urls():
    httpretty.enable()
    httpretty.HTTPretty.allow_net_connect = False

    # smallest valid png, from https://github.com/mathiasbynens/small/blob/master/png-transparent.png
    httpretty.register_uri(
        httpretty.GET,
        PROPER_ICON_URL,
        body=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
        content_type='image/png'
    )
    httpretty.register_uri(
        httpretty.GET,
        IMPROPER_ICON_URL,
        body=b'\n\n\n\n\n\n<!DOCTYPE html>\n<html lang="en">\n  <head>\n',
        content_type='text/html'
    )
    httpretty.register_uri(
        httpretty.GET,
        INVALID_URL
    )
    httpretty.register_uri(
        httpretty.GET,
        TIMEOUT_URL,
        body=exceptionCallback
    )


def get_post_body(icon=PROPER_ICON_URL, home_page=None):
    return {
        'data': {
            'type': 'Source',
            'attributes': {
                'long_title': 'Test User',
                'icon': icon,
                'home_page': home_page
            }
        }
    }


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
            json.dumps(get_post_body()),
            content_type='application/vnd.api+json'
        ).status_code == 401

    def test_improper_scope_post(self, client, share_user, mock_icon_urls):
        assert client.post(
            self.endpoint,
            json.dumps(get_post_body()),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=share_user.authorization(),
        ).status_code == 403

    def test_successful_post_no_home_page(self, client, source_add_user, mock_icon_urls):
        test_data = get_post_body()
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
        created_user = ShareUser.objects.get(pk=IDObfuscator.decode_id(resp_related_share_user['id']))

        assert resp.status_code == 201
        assert resp_attributes['long_title'] == test_data['data']['attributes']['long_title']
        assert resp_attributes['name'] == created_label
        assert resp_attributes['home_page'] is None
        assert resp_related_share_user['attributes']['username'] == created_label
        assert resp_related_share_user['attributes']['authorization_token'] == created_user.accesstoken_set.first().token
        assert created_user.is_trusted is True
        assert resp_related_source_config['label'] == created_label

    def test_successful_post_home_page(self, client, source_add_user, mock_icon_urls):
        test_data = get_post_body(home_page='http://test.homepage.net')
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

    def test_bad_image_url(self, client, source_add_user, mock_icon_urls):
        resp = client.post(
            self.endpoint,
            json.dumps(get_post_body(icon=IMPROPER_ICON_URL)),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.status_code == 400
        assert resp.data[0]['detail'] == 'Could not download/process image.'

    def test_invalid_url(self, client, source_add_user, mock_icon_urls):
        resp = client.post(
            self.endpoint,
            json.dumps(get_post_body(icon=INVALID_URL)),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.status_code == 400
        assert resp.data[0]['detail'] == 'Could not download/process image.'

    def test_timeout_url(self, client, source_add_user, mock_icon_urls):
        resp = client.post(
            self.endpoint,
            json.dumps(get_post_body(icon=TIMEOUT_URL)),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.data[0]['detail'] == 'Could not download/process image.'
