from furl import furl
import pendulum

from django.conf import settings

from share.harvest import BaseHarvester


class MendeleyHarvester(BaseHarvester):
    VERSION = 1
    MENDELEY_OAUTH_URL = 'https://api.mendeley.com/oauth/token'

    def get_token(self):
        """ Mendeley gives tokens that last for one hour. A new token will be
        requested everytime the harvester is run to ensure the access token is
        valid.
        """
        data = {'grant_type': 'client_credentials', 'scope': 'all'}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        r = self.requests.post(
            self.MENDELEY_OAUTH_URL,
            headers=headers,
            data=data,
            auth=(settings.MENDELEY_API_CLIENT_ID, settings.MENDELEY_API_CLIENT_SECRET),
        )
        if r.status_code != 200:
            raise Exception('Access token not granted. Stopping harvest.')
        return r.json()['access_token']

    def do_harvest(self, start_date, end_date):
        if not settings.MENDELEY_API_CLIENT_ID or not settings.MENDELEY_API_CLIENT_SECRET:
            raise Exception('Mendeley authorization information not provided')

        self.requests.headers.update({'Authorization': 'Bearer ' + self.get_token()})

        ACCEPT_HEADER = 'application/vnd.mendeley-public-dataset.1+json'
        headers = {'Accept': ACCEPT_HEADER}

        # Inputs are a DateTime object, many APIs only accept dates
        start_date = start_date.date()

        # Fetch records is a separate function for readability
        # Ends up returning a list of tuples with provider given id and the document itself
        return self.fetch_records(furl(self.config.base_url).set(query_params={
            'modified_since': start_date.isoformat(),
            'fields': 'results.*',
            'limit': '100',  # chance of timing out with larger requests
            'sort': 'publish_date',
            'order': 'asc',
        }).url, headers, end_date)

    def fetch_records(self, url, headers, end_date):

        resp = self.requests.get(url, headers=headers)

        while True:
            for dataset in resp.json()['results']:
                # modified_since filters on publish_date
                if pendulum.parse(dataset['publish_date']) >= end_date:
                    break
                # Send another request to get useful contributor information
                if 'contributors' in dataset:
                    for contributor in dataset['contributors']:
                        try:
                            profile_resp = self.get_contributor_profile(headers, contributor['profile_id'])
                            contributor['full_profile'] = profile_resp.json()
                        except KeyError:
                            continue
                yield (dataset['id'], dataset)

            if 'Link' in resp.headers:
                resp = self.requests.get(resp.links['next']['url'], headers=headers)
            else:
                break

    def get_contributor_profile(self, headers, contributor_uuid):
        ACCEPT_HEADER = 'application/vnd.mendeley-profiles.1+json'
        BASE_PROFILE_URL = 'https://api.mendeley.com/profiles/'

        contributor_headers = {'Accept': ACCEPT_HEADER}
        profile_url = furl(BASE_PROFILE_URL).join(contributor_uuid).url
        return self.requests.get(profile_url, headers=contributor_headers)
