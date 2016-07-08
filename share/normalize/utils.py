from django.conf import settings


def format_doi_as_url(self, doi):
    plain_doi = doi.replace('doi:', '').replace('DOI:', '').strip()
    return settings.DOI_BASE_URL + plain_doi


def format_address(self, address1='', address2='', city='', state_or_province='', postal_code='', country=''):
    if address1 and address2 and city and state_or_province and postal_code and country:
        return '{}\n{}\n{}, {} {}\n{}'.format(address1, address2, city, state_or_province, postal_code, country)

    elif address1 and city and state_or_province and postal_code and country:
        return '{}\n{}, {} {}\n{}'.format(address1, city, state_or_province, postal_code, country)

    elif address1 and address2 and city and state_or_province and postal_code:
        return '{}\n{}\n{}, {} {}'.format(address1, address2, city, state_or_province, postal_code)

    elif address1 and city and state_or_province and postal_code:
        return '{}\n{}, {} {}'.format(address1, city, state_or_province, postal_code)

    elif address1 and address2 and city and state_or_province:
        return '{}\n{}\n{}, {}'.format(address1, address2, city, state_or_province)

    elif address1 and city and state_or_province:
        return '{}\n{}, {}'.format(address1, city, state_or_province)

    elif address1 and address2 and city:
        return '{}\n{}\n{}'.format(address1, address2, city)

    elif address1 and city:
        return '{}\n{}'.format(address1, city)

    elif address1 and address2:
        return '{}\n{}'.format(address1, address2)

    elif city and state_or_province:
        return '{}, {}'.format(city, state_or_province)

    elif city and state_or_province and postal_code:
        return '{}, {} {}'.format(city, state_or_province, postal_code)

    elif city and state_or_province and postal_code and country:
        return '{}, {} {}\n{}'.format(city, state_or_province, postal_code, country)

    return address1
