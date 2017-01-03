def format_address(address1='', address2='', city='', state_or_province='', postal_code='', country=''):
    if address1 and address2 and city and state_or_province and postal_code and country:
        return '{}\n{}\n{}, {} {}\n{}'.format(address1, address2, city, state_or_province, postal_code, country)

    if address1 and city and state_or_province and postal_code and country:
        return '{}\n{}, {} {}\n{}'.format(address1, city, state_or_province, postal_code, country)

    if address1 and address2 and city and state_or_province and postal_code:
        return '{}\n{}\n{}, {} {}'.format(address1, address2, city, state_or_province, postal_code)

    if address1 and city and state_or_province and postal_code:
        return '{}\n{}, {} {}'.format(address1, city, state_or_province, postal_code)

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
