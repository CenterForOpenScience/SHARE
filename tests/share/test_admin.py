import pytest

from share.models import Source


@pytest.mark.django_db
class TestSourceAddForm:

    def test_unique_violation_name(self, admin_client):
        resp = admin_client.post('/admin/share/source/add/', data={
            'title': 'crossref',
            'url': 'http://crossref.org',
        })

        assert resp.status_code == 200
        assert b'Source with this Name already exists.' in resp.content

    def test_unique_violation_long_name(self, admin_client):
        resp = admin_client.post('/admin/share/source/add/', data={
            'title': 'CrossRef',
            'url': 'http://crossref.org',
        })

        assert resp.status_code == 200
        assert b'Source with this Long title already exists.' in resp.content

    @pytest.mark.parametrize('form_data, name, url', [
        ({'title': 'Unique Title', 'url': 'https://osf.com/'}, 'com.osf', 'https://osf.com'),
        ({'title': 'Unique Title', 'url': 'https://share.osf.io/'}, 'io.osf.share', 'https://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'http://share.osf.io/'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'share.osf.io/'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'http://share.osf.io'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'http://Share.osf.io'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'http://SHARE.OSF.IO'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'HTTP://SHARE.OSF.IO'}, 'io.osf.share', 'http://share.osf.io'),
        ({'title': 'Unique Title', 'url': 'HTTP://share.osf.io'}, 'io.osf.share', 'http://share.osf.io'),
    ])
    def test_working_cases(self, admin_client, form_data, name, url):
        resp = admin_client.post('/admin/share/source/add/', data=form_data)

        assert resp.status_code == 302

        source = Source.objects.get(home_page=url)

        assert source.name == name
        assert source.long_title == 'Unique Title'
        assert source.user.username == 'sources.' + name

    @pytest.mark.parametrize('form_data, message', [
        ({'title': 'Unique Name', 'url': 'http://crossref.org'}, b'Source with this Name already exists.'),
        ({'title': 'CrossRef', 'url': 'http://unique.org'}, b'Source with this Long title already exists.'),
        ({'title': '', 'url': 'http://unique.org'}, b'This field is required.'),
        ({'title': 'VT', 'url': 'http://unique.org'}, b'Ensure this value has at least 3 characters (it has 2).'),
        ({'title': 'Unique Name', 'url': ''}, b'This field is required'),
        ({'title': 'Unique Name', 'url': 'somerealllylongworkd'}, b'Enter a valid URL'),
        ({'title': 'A' * 300, 'url': 'http://unique.org'}, b'Ensure this value has at most 255 characters (it has 300).'),
        ({'title': 'Unique Name', 'url': 'http://' + 'A' * 300 + '.com'}, b'Ensure this value has at most 255 characters (it has 311).'),
    ])
    def test_failing_cases(self, admin_client, form_data, message):
        resp = admin_client.post('/admin/share/source/add/', data=form_data)

        assert resp.status_code == 200
        assert message in resp.content
