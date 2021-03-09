import re
from lxml import etree

import logging

from share.transform.chain import exceptions

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
                raise exceptions.InvalidText(datum)

            if first_str and text_list:
                return text_list[0]
        if list_sep is not None:
            return list_sep.join(text_list)
        return text_list

    if data is None:
        return ''

    raise exceptions.InvalidText(data)


def contact_extract(input_string):
    contact_dict = {}
    contact = input_string.replace('Contact:', '').strip()
    contact_email = get_emails(contact)
    contact_name = contact.split('(', 1)[0].strip()
    remove_list = ['Science', 'Division', 'Chair',
                   'Collections', 'Administrative', 'Mycologist and Director',
                   'Director and Curator', 'Director', 'Collection', 'Manager',
                   'Dr.', 'PhD', 'Ph.D.', 'MSc', 'Head', 'Curator', 'Jr.', ' and ',
                   'assistant professor', 'professor', 'herbarium']
    separator_list = ['/', ',']
    for item in remove_list:
        insensitive_item = re.compile(re.escape(item), re.IGNORECASE)
        contact_name = insensitive_item.sub('', contact_name)
    if ',' in contact_name:
        split_name = contact_name.split(',')
        multiple_name = split_name[1].split()
        if len(multiple_name) > 1:
            contact_name = multiple_name[0] + ' ' + split_name[0]
        else:
            contact_name = split_name[1] + ' ' + split_name[0]
    if '/' in contact_name:
        contact_name = contact_name.split('/')[0]
    contact_name = ' '.join([w for w in contact_name.split() if len(w) > 1 or w in separator_list])

    if contact and contact_email:
        contact_dict['email'] = contact_email.strip()
    if contact_name:
        contact_dict['name'] = contact_name.strip()

    return contact_dict


def get_emails(s):
    """Returns first matched email found in string s."""
    # Removing lines that start with '//' because the regular expression
    # mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
    # Adopted from code by Dennis Ideler ideler.dennis@gmail.com
    regex = re.compile((r"([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                        r"{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        r"\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))
    s = s.lower()
    result = re.findall(regex, s)
    if result:
        if not result[0][0].startswith('//'):
            return result[0][0]


def oai_allowed_by_sets(data, blocked_sets=None, approved_sets=None):
    # TODO do this in the Regulator, in a ValidationStep
    blocked_sets = set(blocked_sets or [])
    approved_sets = set(approved_sets or [])
    if blocked_sets or approved_sets:
        set_specs = set(x.replace('publication:', '') for x in etree.fromstring(data).xpath(
            'ns0:header/ns0:setSpec/node()',
            namespaces={'ns0': 'http://www.openarchives.org/OAI/2.0/'}
        ))
        approved = not approved_sets or (set_specs & approved_sets)
        blocked = blocked_sets and (set_specs & blocked_sets)
        if blocked or not approved:
            logger.warning('Discarding datum based on set specs: %s', ', '.join(set_specs))
            return False
    return True
