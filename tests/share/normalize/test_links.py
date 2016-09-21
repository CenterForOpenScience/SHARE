import pytest

from share.normalize.links import OrcidLink


@pytest.mark.parametrize('orcid, result', [
    (None, TypeError('None is not of type str')),
    ('', ValueError(' cannot be expressed as an orcid')),
    ('0000000317011251', 'https://orcid.org/0000-0003-1701-1251'),
    ('0000000229129030', 'https://orcid.org/0000-0002-2912-9030'),
    ('0000000248692412', ValueError('0000000248692412 is not a valid ORCID. Failed checksum')),
    ('0000000248692419', 'https://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
    ('0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
    ('https://orcid.org/0000-0002-1694-233X', 'https://orcid.org/0000-0002-1694-233X'),
    ('https://orcid.org/0000-0002-4869-2419', 'https://orcid.org/0000-0002-4869-2419'),
])
def test_orcid_link(orcid, result):
    if isinstance(result, Exception):
        with pytest.raises(type(result)) as e:
            OrcidLink().execute(orcid)
        assert e.value.args == result.args
    else:
        assert OrcidLink().execute(orcid) == result
