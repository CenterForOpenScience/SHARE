import json
import pytest

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from share.models import Source, ShareUser
from share.util import IDObfuscator
from tests.factories import SourceFactory


PROPER_ICON_URL = 'https://staging-cdn.osf.io/preprints-assets/bitss/square_color_no_transparent.png'
IMPROPER_ICON_URL = 'https://github.com/CenterForOpenScience/SHARE.git'
INVALID_URL = 'invalidURL'
TIMEOUT_URL = 'http://www.timeouturl.com'


def exceptionCallback(request, uri, headers):
    # time.sleep(6)
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


def get_post_body(id=None, **kwargs):
    body = {
        'data': {
            'type': 'Source',
            'attributes': {
                'long_title': 'Test User',
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
        user = next(d for d in included if d['type'] == 'ShareUser')
        flattened['user'] = {
            'id': user['id'],
            **user['attributes']
        }
    return flattened


def fetch_all_pages(client, url, results=None):
    if results is None:
        results = []

    resp = client.get(url)
    assert resp.status_code == 200
    resp_json = resp.json()

    results.extend(resp_json['data'])

    next_url = resp_json['links']['next']
    if next_url:
        return fetch_all_pages(client, next_url, results)
    return results


@pytest.mark.django_db
class TestSourcesGet:
    endpoint = '/api/v2/sources/'

    @pytest.fixture
    def sources(self):
        return [
            SourceFactory(),
            SourceFactory(),
            SourceFactory(),
        ]

    def test_count(self, client, sources):
        sources_qs = Source.objects.exclude(is_deleted=True)
        source_count = sources_qs.count()

        results = fetch_all_pages(client, self.endpoint)

        assert source_count == len(sources) + 1  # auto-created "SHARE System" source
        assert len(results) == source_count

    def test_is_deleted(self, client, sources):
        sources_qs = Source.objects.exclude(is_deleted=True)
        source_count = sources_qs.count()

        sources_before = fetch_all_pages(client, self.endpoint)
        source_ids_before = {s['id'] for s in sources_before}

        assert len(sources_before) == source_count

        deleted_source = sources_qs.last()
        deleted_source.is_deleted = True
        deleted_source.save()

        sources_after = fetch_all_pages(client, self.endpoint)
        source_ids_after = {s['id'] for s in sources_after}

        assert len(sources_after) == len(sources_before) - 1
        missing_ids = {int(i) for i in source_ids_before - source_ids_after}
        assert missing_ids == {deleted_source.id}

    def test_by_id(self, client, sources):
        source = Source.objects.exclude(is_deleted=True).last()
        resp = client.get('{}{}/'.format(self.endpoint, IDObfuscator.encode(source)))

        assert resp.status_code == 200
        assert int(resp.json()['data']['id']) == source.id
        assert resp.json()['data']['type'] == 'Source'
        assert resp.json()['data']['attributes'] == {
            'name': source.name,
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

    def test_improper_scope_post(self, client, share_user):
        assert client.post(
            self.endpoint,
            json.dumps(get_post_body()),
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=share_user.authorization(),
        ).status_code == 403

    def test_successful_post_no_home_page(self, client, source_add_user):
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
        created_user = ShareUser.objects.get(pk=data['user']['id'])
        assert data['source']['longTitle'] == test_data['data']['attributes']['long_title']
        assert data['source']['name'] == created_label
        assert data['source']['homePage'] is None
        assert data['user']['username'] == created_label
        assert data['user']['token'] == created_user.oauth2_provider_accesstoken.first().token
        assert created_user.is_trusted is True

    def test_successful_post_home_page(self, client, source_add_user):
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
        assert data['source']['canonical']

    def test_successful_repost_home_page(self, client, source_add_user):
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

        resp_two_json = resp_two.json()
        if "data" in resp_two_json:
            data_two = flatten_write_response(resp_two)
            assert data_one == data_two
        else:
            if "errors" in resp_two_json:
                assert resp_two_json['errors']['errors'][0]['detail'] == 'That resource already exists.'

    def test_successful_post_put_home_page(self, client, source_add_change_user):
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

    def test_successful_post_patch_home_page(self, client, source_add_change_user):
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

    def test_canonical_source(self, client, source_add_change_user):
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
