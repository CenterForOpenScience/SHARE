from django.conf import settings


def format_doi_as_url(self, doi):
    plain_doi = doi.replace('doi:', '').replace('DOI:', '').strip()
    return settings.DOI_BASE_URL + plain_doi
