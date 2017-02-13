from django.test import override_settings


class TestAPIStatusView:

    @override_settings(VERSION='TESTCASE')
    def test_works(self, client):
        resp = client.get('/api/v2/status/')
        assert resp.status_code == 200
        assert resp.json() == {
            'data': {
                'id': '1',
                'type': 'Status',
                'attributes': {
                    'status': 'up',
                    'version': 'TESTCASE',
                }
            }
        }
