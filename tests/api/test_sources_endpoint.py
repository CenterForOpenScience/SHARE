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
def source_add_change_user():
    content_type = ContentType.objects.get_for_model(Source)
    permission_add = Permission.objects.get(content_type=content_type, codename='add_source')
    permission_change = Permission.objects.get(content_type=content_type, codename='change_source')

    user = ShareUser(username='truly_trusted_tester', is_trusted=True)
    user.save()
    user.user_permissions.add(permission_add)
    user.user_permissions.add(permission_change)

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
    yield
    httpretty.disable()


def get_post_body(icon=PROPER_ICON_URL, id=None, **kwargs):
    body = {
        'data': {
            'type': 'Source',
            'attributes': {
                'long_title': 'Test User',
                'icon_url': icon,
                **kwargs
            }
        }
    }
    if id is not None:
        body['data']['id'] = id
    return body


def flatten_write_response(resp):
    json = resp.json()
    flattened = {
        'source': {
            'id': json['data']['id'],
            **json['data']['attributes']
        }
    }
    included = json.get('included')
    if included:
        source_config = next(d for d in included if d['type'] == 'SourceConfig')
        flattened['sourceConfig'] = {
            'id': source_config['id'],
            **source_config['attributes']
        }
        user = next(d for d in included if d['type'] == 'ShareUser')
        flattened['user'] = {
            'id': user['id'],
            **user['attributes']
        }
    return flattened


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

    def test_by_id(self, client):
        source = Source.objects.first()
        resp = client.get('{}{}/'.format(self.endpoint, IDObfuscator.encode(source)))

        assert resp.status_code == 200
        assert IDObfuscator.load(resp.json()['data']['id']) == source
        assert resp.json()['data']['type'] == 'Source'
        assert resp.json()['data']['attributes'] == {
            'name': source.name,
            'icon': 'http://testserver{}'.format(source.icon.url),
            'homePage': source.home_page,
            'longTitle': source.long_title,
        }


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
        assert resp.status_code == 201
        data = flatten_write_response(resp)

        created_label = data['source']['longTitle'].replace(' ', '_').lower()
        created_user = ShareUser.objects.get(pk=IDObfuscator.decode_id(data['user']['id']))

        assert data['source']['longTitle'] == test_data['data']['attributes']['long_title']
        assert data['source']['name'] == created_label
        assert data['source']['homePage'] is None
        assert data['user']['username'] == created_label
        assert data['user']['token'] == created_user.accesstoken_set.first().token
        assert created_user.is_trusted is True
        assert data['sourceConfig']['label'] == created_label

    def test_successful_post_home_page(self, client, source_add_user, mock_icon_urls):
        test_data = get_post_body(home_page='http://test.homepage.net')
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )
        assert resp.status_code == 201
        data = flatten_write_response(resp)

        assert data['source']['longTitle'] == test_data['data']['attributes']['long_title']
        assert data['source']['homePage'] == test_data['data']['attributes']['home_page']
        assert not data['source']['canonical']

    def test_successful_repost_home_page(self, client, source_add_user, mock_icon_urls):
        test_data = get_post_body(home_page='http://test.homepage.net')
        resp_one = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp_one.status_code == 201
        data_one = flatten_write_response(resp_one)

        # Second Request CONFLICT returns data
        resp_two = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )
        assert resp_two.status_code == 409

        data_two = flatten_write_response(resp_two)

        assert data_one == data_two

    def test_successful_post_put_home_page(self, client, source_add_change_user, mock_icon_urls):
        test_data = get_post_body(home_page='http://test.homepage.net')
        resp_one = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )

        assert resp_one.status_code == 201
        data_one = flatten_write_response(resp_one)

        source_url = '{}{}/'.format(self.endpoint, data_one['source']['id'])

        new_home_page = 'http://test2.homepage.net'
        test_two_data = get_post_body(home_page=new_home_page, id=data_one['source']['id'])
        test_two_data['data']['attributes']['name'] = data_one['source']['name']

        resp_two = client.put(
            source_url,
            json.dumps(test_two_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )
        assert resp_two.status_code == 200

        data_two = flatten_write_response(resp_two)

        assert data_two['source']['homePage'] == new_home_page
        assert data_one != data_two

    def test_successful_post_patch_home_page(self, client, source_add_change_user, mock_icon_urls):
        test_data = get_post_body(home_page='http://test.homepage.net')
        resp_one = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )

        assert resp_one.status_code == 201
        data_one = flatten_write_response(resp_one)

        source_url = '{}{}/'.format(self.endpoint, data_one['source']['id'])

        new_home_page = 'http://test2.homepage.net'
        test_two_data = get_post_body(id=data_one['source']['id'], home_page=new_home_page)

        resp_two = client.patch(
            source_url,
            json.dumps(test_two_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )
        assert resp_two.status_code == 200

        data_two = flatten_write_response(resp_two)

        assert data_two['source']['homePage'] == new_home_page
        assert data_one != data_two

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
        assert resp.data[0]['detail'] == 'Enter a valid URL.'

    def test_timeout_url(self, client, source_add_user, mock_icon_urls):
        resp = client.post(
            self.endpoint,
            json.dumps(get_post_body(icon=TIMEOUT_URL)),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_user.authorization(),
        )

        assert resp.data[0]['detail'] == 'Could not download/process image.'

    def test_canonical_source(self, client, source_add_change_user, mock_icon_urls):
        # add a canonical source
        test_data = get_post_body(canonical=True)
        resp = client.post(
            self.endpoint,
            json.dumps(test_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )
        assert resp.status_code == 201
        data_one = flatten_write_response(resp)

        assert data_one['source']['canonical']

        # update it to be noncanonical
        source_url = '{}{}/'.format(self.endpoint, data_one['source']['id'])
        test_two_data = get_post_body(id=data_one['source']['id'], canonical=False)

        resp_two = client.patch(
            source_url,
            json.dumps(test_two_data),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=source_add_change_user.authorization(),
        )
        assert resp_two.status_code == 200
        data_two = flatten_write_response(resp_two)

        assert not data_two['source']['canonical']
