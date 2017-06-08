import logging

logger = logging.getLogger(__name__)


def format_address(address1='', address2='', city='', state_or_province='', postal_code='', country=''):
    if address1 and address2 and city and state_or_province and postal_code and country:
        return '{}\n{}\n{}, {} {}\n{}'.format(address1, address2, city, state_or_province, postal_code, country)

    if address1 and city and state_or_province and postal_code and country:
        return '{}\n{}, {} {}\n{}'.format(address1, city, state_or_province, postal_code, country)

    if address1 and address2 and city and state_or_province and postal_code:
        return '{}\n{}\n{}, {} {}'.format(address1, address2, city, state_or_province, postal_code)

    if address1 and city and state_or_province and postal_code:
        return '{}\n{}, {} {}'.format(address1, city, state_or_province, postal_code)

    if address1 and city and state_or_province and country:
        return '{}\n{}, {}\n{}'.format(address1, city, state_or_province, country)

    if address1 and address2 and city and state_or_province:
        return '{}\n{}\n{}, {}'.format(address1, address2, city, state_or_province)

    if address1 and city and state_or_province:
        return '{}\n{}, {}'.format(address1, city, state_or_province)

    if address1 and address2 and city:
        return '{}\n{}\n{}'.format(address1, address2, city)

    if address1 and city:
        return '{}\n{}'.format(address1, city)

    if address1 and address2:
        return '{}\n{}'.format(address1, address2)

    if city and state_or_province and postal_code and country:
        return '{}, {} {}\n{}'.format(city, state_or_province, postal_code, country)

    if city and state_or_province and postal_code:
        return '{}, {} {}'.format(city, state_or_province, postal_code)

    if city and state_or_province:
        return '{}, {}'.format(city, state_or_province)

    return address1


def force_text(data, list_sep=None, first_str=False):
    if isinstance(data, dict):
        return data.get('#text', '')

    if isinstance(data, str):
        return data

    if isinstance(data, list):
        text_list = []
        for datum in (data or []):
            if datum is None:
                continue
            if isinstance(datum, dict):
                if '#text' not in datum:
                    logger.warning('Skipping %s, no #text key exists', datum)
                    continue
                text_list.append(datum['#text'])
            elif isinstance(datum, str):
                text_list.append(datum)
            else:
                raise Exception(datum)

            if first_str and text_list:
                return text_list[0]
        if list_sep is not None:
            return list_sep.join(text_list)
        return text_list

    if data is None:
        return ''

    raise TypeError(data)
