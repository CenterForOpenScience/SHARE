from collections import deque
from functools import reduce
import json
import logging
import re
import threading
import dateutil
import urllib
import types

import xmltodict

import pendulum

from lxml import etree

from pycountry import languages

from nameparser import HumanName

from share.util import iris, DictHashingDict

logger = logging.getLogger(__name__)


__all__ = ('ParseDate', 'ParseName', 'ParseLanguage', 'Trim', 'Concat', 'Map', 'Delegate', 'Maybe', 'XPath', 'Join', 'RunPython', 'Static', 'Try', 'Subjects', 'OneOf', 'Orcid', 'DOI', 'IRI', 'GuessAgentType', 'Filter', 'Unique', 'Int')


#### Public API ####

def ParseDate(chain):
    return chain + DateParserLink()


def ParseName(chain):
    return chain + NameParserLink()


def ParseLanguage(chain):
    return chain + LanguageParserLink()


def Trim(chain):
    return chain + TrimLink()


def Concat(*chains, deep=False):
    return ConcatLink(*chains, deep=deep)


def XPath(chain, path):
    return chain + XPathLink(path)


def Join(chain, joiner='\n'):
    return chain + JoinLink(joiner=joiner)


def Maybe(chain, segment, default=None):
    return chain + MaybeLink(segment, default=default)


def Try(chain, default=None, exceptions=None):
    return TryLink(chain, default=default, exceptions=exceptions)


def Map(chain, *chains):
    return Concat(*chains) + IteratorLink() + chain


def Delegate(parser, chain=None):
    if chain:
        return chain + DelegateLink(parser)
    return DelegateLink(parser)


def RunPython(function_name, chain=None, *args, **kwargs):
    if chain:
        return chain + RunPythonLink(function_name, *args, **kwargs)
    return RunPythonLink(function_name, *args, **kwargs)


def Static(value):
    return StaticLink(value)


def Subjects(*chains):
    return Concat(Map(MapSubjectLink(), *chains), deep=True)


def OneOf(*chains):
    return OneOfLink(*chains)


def Orcid(chain=None):
    if chain:
        return (chain + OrcidLink()).IRI
    return OrcidLink().IRI


def DOI(chain=None):
    if chain:
        return (chain + DOILink()).IRI
    return DOILink().IRI


def IRI(chain=None, urn_fallback=False):
    if chain:
        return (chain + IRILink(urn_fallback=urn_fallback)).IRI
    return IRILink(urn_fallback=urn_fallback).IRI


def GuessAgentType(chain=None, default=None):
    if chain:
        return chain + GuessAgentTypeLink(default=default)
    return GuessAgentTypeLink(default=default)


def Filter(func, *chains):
    return Concat(*chains) + FilterLink(func)


def Unique(chain=None):
    if chain:
        return AbstractLink.__add__(chain, UniqueLink())
    return UniqueLink()


def Int(chain):
    return chain + IntLink()


### /Public API
# BaseClass for all links
# Links are a single step of the parsing process
# Links may not mutate the object passed into them
# A chain is any number of links added together
class AbstractLink:

    def __init__(self, _next=None, _prev=None):
        # next and prev are generally set by the __add__ method
        self._next = _next
        self._prev = _prev

        # Every chain must start with an AnchorLink
        if self._prev is None and not isinstance(self, AnchorLink):
            AnchorLink() + self

    # Build the entire chain this link is a part of
    # NOTE: This results in the entire chain rather than starting from the current link
    def chain(self):
        first = self
        while first._prev:
            first = first._prev
        deq = deque([first])
        while deq[-1]._next:
            deq.append(deq[-1]._next)
        return tuple(deq)

    # Transformation logic goes here
    def execute(self, obj):
        raise NotImplementedError()

    # Add a link into an existing chain
    def __add__(self, step):
        self._next = step
        step._prev = self
        return step

    def __radd__(self, other):
        return self + PrependLink(other)

    # For handling paths that are not valid python
    # or are already used. IE text, execute, oai:title
    # ctx('oai:title')
    def __getitem__(self, name):
        if isinstance(name, int):
            return self + IndexLink(name)
        if isinstance(name, str):
            return self + PathLink(name)
        raise Exception(
            '__getitem__ only accepts integers and strings\n'
            'Found {}'.format(name)
        )
        # raise Exception

    # Reserved for special cases
    # Any other use is an error
    def __call__(self, name):
        if name == '*':
            return self + IteratorLink()
        if name == 'index':
            return self + GetIndexLink()
        raise Exception(
            '"{}" is not a action that __call__ can resolve\n'
            '__call__ is reserved for special actions\n'
            'If you are trying to access an element use dictionary notation'.format(name)
        )

    # The preferred way of building paths.
    # Can express either json paths or xpaths
    # ctx.root.nextelement[0].first_item_attribute
    def __getattr__(self, name):
        if name[0] == '_':
            raise AttributeError(
                '{} has no attribute {}\n'
                'NOTE: "_"s are reserved for accessing private attributes\n'
                'Use dictionary notation to access elements beginning with "_"s\n'.format(self, name)
            )
        return self + PathLink(name)

    def __repr__(self):
        return '<{}()>'.format(self.__class__.__name__)

    def run(self, obj):
        Context().frames.append({'link': self, 'context': obj, 'parser': Context().parser})
        try:
            return self.execute(obj)
        finally:
            Context().frames.pop(-1)


# The begining link for all chains
# Contains logic for executing a chain against an object
# Adding another link to an anchor will result in a copy of the
# original anchor
class AnchorLink(AbstractLink):

    def execute(self, obj):
        return reduce(lambda acc, cur: cur.run(acc), self.chain()[1:], obj)


class Context(AnchorLink):

    __CONTEXT = threading.local()

    @property
    def jsonld(self):
        return {
            '@graph': self.graph,
            '@context': {}
        }

    def __init__(self):
        if not hasattr(Context.__CONTEXT, '_ctxdict'):
            Context.__CONTEXT._ctxdict = {}
            self.clear()
        super().__init__()

    @property
    def parser(self):
        return self.parsers[-1] if self.parsers else None

    def clear(self):
        self.graph = []
        self.frames = []
        self.parsers = []
        self._config = None
        self.pool = DictHashingDict()

    def __add__(self, step):
        return AnchorLink() + step

    def __radd__(self, other):
        raise NotImplementedError()

    def __setattr__(self, name, value):
        if not hasattr(Context.__CONTEXT, '_ctxdict'):
            self.__init__()
        Context.__CONTEXT._ctxdict[name] = value

    def __getattr__(self, name):
        if not hasattr(Context.__CONTEXT, '_ctxdict'):
            self.__init__()
        try:
            return Context.__CONTEXT._ctxdict[name]
        except KeyError:
            return super().__getattr__(name)


class NameParserLink(AbstractLink):
    def execute(self, obj):
        return HumanName(obj)


class DateParserLink(AbstractLink):
    LOWER_BOUND = pendulum.create(1200, 1, 1)
    UPPER_BOUND = pendulum.today().add(years=100)
    DEFAULT = pendulum.create(2016, 1, 1)

    def execute(self, obj):
        if obj:
            date = dateutil.parser.parse(obj, default=self.DEFAULT)
            repr(date)  # Forces tzoffset validation to run
            if date < self.LOWER_BOUND:
                raise ValueError('{} is before the lower bound {}.'.format(obj, self.LOWER_BOUND.isoformat()))
            if date > self.UPPER_BOUND:
                raise ValueError('{} is after the upper bound {}.'.format(obj, self.UPPER_BOUND.isoformat()))
            return date.in_tz('UTC').isoformat()
        raise ValueError('{} is not a valid date.'.format(obj))


class LanguageParserLink(AbstractLink):
    def execute(self, maybe_code):
        if isinstance(maybe_code, dict):
            maybe_code = maybe_code['#text']
        # Force indices to populate
        if not languages._is_loaded:
            languages._load()

        for kwarg in languages.indices.keys():
            try:
                return languages.get(**{kwarg: maybe_code}).iso639_3_code
            except KeyError:
                continue
        return None


class ConcatLink(AbstractLink):
    def __init__(self, *chains, deep=False):
        self._chains = chains
        self._deep = deep
        super().__init__()

    def _concat(self, acc, val):
        if val is None:
            return acc
        if not isinstance(val, list):
            val = [val]
        elif self._deep:
            val = reduce(self._concat, val, [])
        return acc + [v for v in val if v != '' and v is not None]

    def execute(self, obj):
        return reduce(self._concat, [
            chain.chain()[0].run(obj)
            for chain in self._chains
        ], [])


class JoinLink(AbstractLink):
    def __init__(self, joiner='\n'):
        self._joiner = joiner
        super().__init__()

    def execute(self, obj):
        obj = obj or []
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
        return self._joiner.join(x for x in obj if x)


class TrimLink(AbstractLink):
    def execute(self, obj):
        return obj.strip()


class IteratorLink(AbstractLink):
    def __init__(self):
        super().__init__()
        self.__anchor = AnchorLink()

    def __add__(self, step):
        # Attach all new links to the "subchain"
        chain = list(step.chain())
        while isinstance(chain[0], AnchorLink):
            chain.pop(0)

        self.__anchor.chain()[-1] + chain[0]
        return self

    def execute(self, obj):
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
        return [self.__anchor.run(sub) for sub in obj]


class MaybeLink(AbstractLink):
    def __init__(self, segment, default=None):
        super().__init__()
        self._segment = segment
        self._default = default
        self.__anchor = AnchorLink()

    def __add__(self, step):
        # Attach all new links to the "subchain"
        self.__anchor.chain()[-1] + step
        return self

    def execute(self, obj):
        if not obj:
            return []
        val = obj.get(self._segment)
        if val:
            return self.__anchor.run(val)
        if len(Context().frames) > 1 and isinstance(Context().frames[-2]['link'], (IndexLink, IteratorLink, ConcatLink, JoinLink)):
            return []
        return self._default


class TryLink(AbstractLink):
    def __init__(self, chain, default=None, exceptions=None):
        super().__init__()
        self._chain = chain
        self._default = default
        self.__anchor = AnchorLink()
        self._exceptions = (IndexError, KeyError) + (exceptions or ())

    def __add__(self, step):
        # Attach all new links to the "subchain"
        self.__anchor.chain()[-1] + step
        return self

    def execute(self, obj):
        try:
            val = self._chain.chain()[0].run(obj)
        except self._exceptions:
            return self._default
        except TypeError as err:
            logger.debug('TypeError: {}. When trying to access {}'.format(err, self._chain.chain()))
            return self._default
        return self.__anchor.run(val)


class PathLink(AbstractLink):
    def __init__(self, segment):
        self._segment = segment
        super().__init__()

    def execute(self, obj):
        return obj[self._segment]

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self._segment)


class IndexLink(AbstractLink):
    def __init__(self, index):
        self._index = index
        super().__init__()

    def execute(self, obj):
        return obj[self._index]

    def __repr__(self):
        return '<{}([{}])>'.format(self.__class__.__name__, self._index)


class GetIndexLink(AbstractLink):
    def execute(self, obj):
        for frame in Context().frames[::-1]:
            if isinstance(frame['link'], IteratorLink):
                return frame['context'].index(obj)
        return -1
        # return Context().parent.index(obj)


class PrependLink(AbstractLink):
    def __init__(self, string):
        self._string = string
        super().__init__()

    def execute(self, obj):
        return self._string + obj


class XPathLink(AbstractLink):
    def __init__(self, xpath):
        self._xpath = xpath
        super().__init__()

    def execute(self, obj):
        unparsed_obj = xmltodict.unparse(obj)
        xml_obj = etree.XML(unparsed_obj.encode())
        elem = xml_obj.xpath(self._xpath)
        elems = [xmltodict.parse(etree.tostring(x)) for x in elem]
        if len(elems) == 1 and not isinstance(self._next, (IndexLink, IteratorLink)):
            return elems[0]
        return elems

    def __repr__(self):
        return '<{}({!r})>'.format(self.__class__.__name__, self._xpath)


class DelegateLink(AbstractLink):
    def __init__(self, parser):
        self._parser = parser
        super().__init__()

    def execute(self, obj):
        # callable will return True for classes as well as functions
        if isinstance(self._parser, types.FunctionType):
            parser = self._parser(obj)
            return parser(obj).parse()
        return self._parser(obj).parse()


class RunPythonLink(AbstractLink):
    def __init__(self, function_name, *args, **kwargs):
        self._function_name = function_name
        self._args = args
        self._kwargs = kwargs
        super().__init__()

    def execute(self, obj):
        if callable(self._function_name):
            return self._function_name(obj, *self._args, **self._kwargs)
        return getattr(Context().parser, self._function_name)(obj, *self._args, **self._kwargs)


class StaticLink(AbstractLink):
    def __init__(self, value):
        self._value = value
        super().__init__()

    def execute(self, obj):
        return self._value


class MapSubjectLink(AbstractLink):

    with open('./share/models/synonyms.json') as fobj:
        MAPPING = json.load(fobj)

    def execute(self, obj):
        if not obj:
            return None

        if isinstance(obj, list):
            return [self.execute(x) for x in obj]

        assert isinstance(obj, str), 'Subjects must be strings. Got {}.'.format(type(obj))

        mapped = self.MAPPING.get(obj.lower())

        if not mapped:
            logger.debug('No synonyms found for term "%s"', obj)

        return mapped


class OneOfLink(AbstractLink):

    def __init__(self, *chains):
        self._chains = chains
        super().__init__()

    def execute(self, obj):
        errors = []
        for chain in self._chains:
            try:
                return chain.chain()[0].run(obj)
            except Exception as e:
                errors.append(e)

        raise Exception('All chains failed {}'.format(errors))


class AbstractIRILink(AbstractLink):
    """Normalize IRIs
    """
    SAFE_SEGMENT_CHARS = ":@-._~!$&'()*+,;="  # https://github.com/gruns/furl/blob/master/furl/furl.py#L385

    @classmethod
    def hint(cls, obj):
        """A percentage expressed as a float of how likely a the given object can be parsed as this class
        """
        raise NotImplementedError()

    def execute(self, obj):
        if not isinstance(obj, str):
            raise TypeError('\'{}\' is not of type str.'.format(obj))

        parsed = self._parse(obj)
        parsed = self._process(**parsed)
        return iris.parse(iris.compose(**parsed))

    def _parse(self, obj):
        return iris.parse(obj)

    def _process(self, **attrs):
        processed = {}
        for key in sorted(attrs.keys()):
            if hasattr(self, '_process_' + key):
                processed[key] = getattr(self, '_process_' + key)(attrs[key])
        return processed

    def _process_scheme(self, scheme):
        return scheme.lower()

    def _process_authority(self, authority):
        return authority.lower()

    def _process_path(self, path):
        return path

    def _process_query(self, query):
        return query

    def _process_fragment(self, fragment):
        return fragment or None


class ISSNLink(AbstractIRILink):

    ISSN_RE = re.compile(r'(?:^|\s+)(\d{4})-(\d{3}[\dxX])\s*$')

    @classmethod
    def hint(cls, obj):
        if re.search(cls.ISSN_RE, obj):
            return 0.9
        return int('issn' in obj) * 0.35

    @classmethod
    def checksum(cls, digits):
        total, checksum = 0, digits[-1]
        for i, digit in enumerate(digits[:-1]):
            total += (8 - i) * int(digit)
        actual = (11 - (total % 11)) % 11
        if actual == 10:
            actual = 'X'
        if checksum != str(actual):
            raise ValueError('\'{}\' is not a valid ISSN; failed checksum.'.format(digits))

    def _parse(self, obj):
        match = re.search(self.ISSN_RE, obj.upper())
        if not match:
            raise ValueError('\'{}\' cannot be expressed as an ISSN.'.format(obj))
        self.checksum(''.join(match.groups()))

        return {
            'scheme': 'urn',
            'authority': 'ISSN',
            'path': '/{}-{}'.format(*match.groups())
        }


class URNLink(AbstractIRILink):
    SCHEMES = {'urn', 'oai'}
    URN_RE = re.compile(r'\b({schemes}):((?:\w|[.-])+):(\S+)'.format(schemes='|'.join(SCHEMES)), flags=re.I)
    PARSED_URN_RE = re.compile(r'^({schemes})://([^/\s]+)/(\S+)$'.format(schemes='|'.join(SCHEMES)), flags=re.I)

    @classmethod
    def hint(cls, obj):
        if cls.URN_RE.search(obj) is not None:
            return 0.9
        if cls.PARSED_URN_RE.search(obj) is not None:
            return 0.9
        return 0.0

    def _parse(self, obj):
        match = self.URN_RE.search(obj.lower()) or self.PARSED_URN_RE.search(obj.lower())
        if not match:
            raise ValueError('\'{}\' is not a valid URN.'.format(obj))

        return {
            'scheme': match.group(1),
            'authority': match.group(2),
            'path': '/{}'.format(match.group(3))
        }


class ISNILink(AbstractIRILink):
    DOMAIN = 'isni.org'
    SCHEME = 'http'

    FORMAT = 'ISNI'
    FORMAT_STR = '/{}{}{}{}'

    BOUNDS = (
        # (lower, upper)
        (None, 150000007),
        (350000001, None),
    )
    ISNI_RE = re.compile(r'^(?:https?://)?[^\B=/\d]*/?(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}(?:\d|x))\b', re.I)

    @classmethod
    def hint(cls, obj):
        try:
            cls().execute(obj)
        except ValueError:
            return 0
        return 1.0

    @classmethod
    def checksum(cls, digits):
        total, checksum = 0, digits[-1]
        for digit in digits[:-1]:
            total = (total + int(digit, 36)) * 2
        check = (12 - (total % 11)) % 11
        literal = (int(digits[:-1]) * 10) + check
        if check == 10:
            check = 'X'
        if str(check) != checksum:
            raise ValueError('\'{}\' is not a valid {}; failed checksum.'.format(digits, cls.FORMAT))
        for lower, upper in cls.BOUNDS:
            if (not lower or lower < literal) and (not upper or upper > literal):
                return
        raise ValueError('\'{0}\' is outside reserved {1} range.'.format(digits, cls.FORMAT, lower, upper))

    def _parse(self, obj):
        match = re.search(self.ISNI_RE, obj.upper())
        if not match:
            raise ValueError('\'{}\' cannot be expressed as an {}.'.format(obj, self.FORMAT))
        self.checksum(''.join(match.groups()))

        return {
            'scheme': self.SCHEME,
            'authority': self.DOMAIN,
            'path': self.FORMAT_STR.format(*match.groups())
        }


class OrcidLink(ISNILink):
    """Reformat Orcids to the cannonical form
    https://orcid.org/xxx-xxxx-xxxx-xxxx

    0000000248692419
    0000-0002-4869-2419
    https://orcid.org/0000-0002-4869-2419

    Any of the above would be transformed into https://orcid.org/0000-0002-4869-2419

    ORCID is a subset of the International Standard Name Identifier (ISNI) in the range 0000-0001-5000-0007 to 0000-0003-5000-0001.
    """
    DOMAIN = 'orcid.org'
    SCHEME = 'http'

    FORMAT = 'ORCID'
    FORMAT_STR = '/{}-{}-{}-{}'

    BOUNDS = (
        (150000007, 350000001),
    )


class DOILink(AbstractIRILink):
    """Reformt DOIs to the cannonical form

    * All DOIs will be valid URIs
    * All DOIs will use https
    * All DOI paths will be uppercased

    Reference:
        https://www.doi.org/doi_handbook/2_Numbering.html
        https://stackoverflow.com/questions/27910/finding-a-doi-in-a-document-or-page

    While having characters like <>[] in URLs is technically valid, rfc3987 does not seem to like.
    For that reason we escape them here using furl. The regex ensure we won't pick up invalid URLS
    """

    DOI_SCHEME = 'http'
    DOI_DOMAIN = 'dx.doi.org'
    DOI_RE = re.compile(r'^(?:https?://)?[^\B=/]*/?(10\.\d{4,}(?:\.\d+)*(?:/|%2F)\S+(?:(?![\"&\'<>])))\b', re.I)

    @classmethod
    def hint(cls, obj):
        if cls.DOI_RE.search(obj) is not None:
            return 0.9
        return 0

    def _process_scheme(self, _):
        return self.DOI_SCHEME

    def _process_authority(self, _):
        return self.DOI_DOMAIN

    def _parse(self, obj):
        match = self.DOI_RE.search(obj.upper())
        if not match:
            raise ValueError('\'{}\' is not a valid DOI.'.format(obj))
        return {
            'scheme': None,
            'authority': None,
            'path': '/' + '/'.join(urllib.parse.quote(x, safe=self.SAFE_SEGMENT_CHARS) for y in match.groups() for x in urllib.parse.unquote(y).split('/'))
        }


class URLLink(AbstractIRILink):
    SCHEMES = {'http', 'https', 'ftp', 'ftps'}
    SCHEMELESS_STARTS = ('www.', 'www2.')
    IMPLICIT_PORTS = {80, 443}
    IP_RE = re.compile(r'\b({schemes})://(\d{{1,3}}.){{4}}(?:\d{{2,5}})\b([-a-z0-9@:%_\+.~#?&//=]*)'.format(schemes='|'.join(SCHEMES)), flags=re.I)
    URL_RE = re.compile(r'\b({schemes})://[-a-z0-9@:%._\+~#=]{{2,256}}\.[a-z]{{2,6}}\b([-a-z0-9@:%_\+.~#?&//=]*)'.format(schemes='|'.join(SCHEMES)), flags=re.I)

    @classmethod
    def hint(cls, obj):
        # BePress double escapes in OAI feeds
        obj = obj.replace('&amp;', '&')

        if cls.URL_RE.search(obj) is not None:
            return 0.25
        if cls.IP_RE.search(obj) is not None:
            return 0.25
        if obj.lower().startswith(cls.SCHEMELESS_STARTS):
            return 0.1
        return 0

    def _parse(self, obj):
        # BePress double escapes in OAI feeds
        obj = obj.replace('&amp;', '&')

        match = self.URL_RE.search(obj) or self.IP_RE.search(obj)
        if not match and obj.lower().startswith(self.SCHEMELESS_STARTS):
            match = self.URL_RE.search('http://{}'.format(obj))
        return super(URLLink, self)._parse(match.group(0))

    def _process_scheme(self, scheme):
        scheme = scheme.lower()
        if scheme not in self.SCHEMES:
            raise ValueError('\'{}\' is not a valid scheme for URLs.'.format(scheme))
        return scheme.rstrip('s')  # Standardize on non-secure

    def _process_query(self, query):
        return query  # TODO Order me

    def _process_authority(self, authority):
        authority = super()._process_authority(authority)
        if ':' in authority:
            host, port = authority.split(':')
            if port and int(port) in self.IMPLICIT_PORTS:
                authority = host
        return authority


class EmailLink(AbstractIRILink):

    EMAIL_RE = re.compile(r'(?P<scheme>mailto:)?(?P<mailbox>[éa-zA-Z0-9_.+-]+)@(?P<authority>[a-zA-Z0-9\u2010ü-]+\.[a-zA-Z0-9-.]+)')  # http://emailregex.com/

    @classmethod
    def hint(self, obj):
        if self.EMAIL_RE.search(obj) is not None:
            return 1.0
        return 0

    def execute(self, obj):
        if not isinstance(obj, str):
            raise TypeError('\'{}\' is not of type str.'.format(obj))
        # Handle unicode hyphens
        emails = self.EMAIL_RE.findall(obj.replace('\u2010', '-'))
        if len(emails) < 1:
            raise ValueError('\'{}\'is not a valid email address.'.format(obj))
        if len(emails) > 1:
            raise ValueError('Found many email addresses in \'{}\'.'.format(obj))
        return {
            'scheme': 'mailto',
            'authority': emails[0][2],
            'IRI': 'mailto:{1}@{2}'.format(*emails[0])
        }


class ArXivLink(AbstractIRILink):
    # https://arxiv.org/help/arxiv_identifier

    ARXIV_SCHEME = 'http'
    ARXIV_DOMAIN = 'arxiv.org'
    ARXIV_PATH = '/abs/{}'
    ARXIV_RE = re.compile(r'\barXiv:(\d{4}.\d{5})(v\d)?', flags=re.I)

    @classmethod
    def hint(cls, obj):
        if cls.ARXIV_RE.search(obj) is not None:
            return 1.0
        return 0

    def _parse(self, obj):
        match = self.ARXIV_RE.search(obj)
        if not match:
            raise ValueError('\'{}\' is not a valid ArXiv Identifier.'.format(obj))
        return {
            'scheme': self.ARXIV_SCHEME,
            'authority': self.ARXIV_DOMAIN,
            'path': self.ARXIV_PATH.format(match.group(1))
        }


class ARKLink(AbstractIRILink):
    # https://en.wikipedia.org/wiki/Archival_Resource_Key
    # https://wiki.ucop.edu/download/attachments/16744455/arkspec.pdf

    ARK_SCHEME = 'ark'
    ARK_RE = re.compile(r'\bark://?(\d+)(/\S+)', flags=re.I)

    @classmethod
    def hint(cls, obj):
        if cls.ARK_RE.search(obj) is not None:
            return 0.9
        return 0

    def _parse(self, obj):
        match = self.ARK_RE.search(obj)
        if not match:
            raise ValueError('\'{}\' is not a valid ARK Identifier.'.format(obj))
        return {
            'scheme': self.ARK_SCHEME,
            'authority': match.group(1),
            'path': match.group(2)
        }


class InfoURILink(AbstractIRILink):
    'info:eu-repo/grantAgreement/EC/FP7/280632/'
    # http://info-uri.info/registry/docs/misc/faq.html
    # https://tools.ietf.org/html/rfc4452

    SCHEME = 'info'
    INFO_RE = re.compile('^\s*info:([\w-]+)(/\S+)\s*$')

    @classmethod
    def hint(cls, obj):
        if cls.INFO_RE.search(obj) is not None:
            return 0.9
        return 0

    def _parse(self, obj):
        match = self.INFO_RE.search(obj)
        if not match:
            raise ValueError('\'{}\' is not a valid Info URI.'.format(obj))
        return {
            'scheme': self.SCHEME,
            'authority': match.group(1),
            'path': match.group(2)
        }


class ISBNLink(AbstractIRILink):
    SCHEME = 'urn'
    AUTHORITY = 'isbn'
    ISBN10_RE = re.compile('^(?:urn:\/\/isbn\/|ISBN:? ?)?(\d\d?)-(\d{3,7})-(\d{1,6})-(\d|x)$', re.I)
    ISBN13_RE = re.compile('^(?:urn://isbn/|ISBN:? ?)?(978|979)-(\d\d?)-(\d{3,5})-(\d{2,5})-(\d)$', re.I)

    @classmethod
    def hint(cls, obj):
        if cls.ISBN13_RE.match(obj) or cls.ISBN10_RE.match(obj):
            return 1.0
        return 0

    def _parse(self, obj):
        match = self.ISBN13_RE.match(obj.upper()) or self.ISBN10_RE.match(obj.upper())

        if not match or len(''.join(match.groups())) not in (13, 10):
            raise ValueError('\'{}\' cannot be expressed as an ISBN.'.format(obj))

        if match.re == self.ISBN13_RE:
            digits = ''.join(match.groups())
            check = (10 - sum(int(x) * (i % 2 * 2 + 1) for i, x in enumerate(digits[:-1])) % 10) % 10

            if str(check) != digits[-1]:
                raise ValueError('\'{}\' is not a valid ISBN; failed checksum.'.format(obj))

        if match.re == self.ISBN10_RE:
            digits = ''.join(match.groups())
            check = sum(10 if x == 'X' else int(x) * (10 - i) for i, x in enumerate(digits))

            if check % 11 != 0:
                raise ValueError('\'{}\' is not a valid ISBN; failed checksum.'.format(obj))

            # Add prefix and compute new checksum
            digits = '978' + digits
            digits = digits[:-1] + str((10 - sum(int(x) * (i % 2 * 2 + 1) for i, x in enumerate(digits[:-1])) % 10) % 10)

        return {
            'scheme': self.SCHEME,
            'authority': self.AUTHORITY,
            # NOTE: the - seperated format is not standardized for ISBNS
            # this format is being used as it groups digits by meaning
            # EAN - Group - Publisher - Title - Check
            # https://en.wikipedia.org/wiki/International_Standard_Book_Number#/media/File:ISBN_Details.svg
            'path': '/{}{}{}-{}{}-{}{}{}{}-{}{}{}-{}'.format(*digits)
        }


class IRILink(AbstractLink):
    FALLBACK_FORMAT = 'urn:share:{source}:{id}'

    def __init__(self, urn_fallback=False):
        super().__init__()
        self._urn_fallback = urn_fallback

    @classmethod
    def iri_links(cls, base=AbstractIRILink):
        for link in base.__subclasses__():
            yield link
            yield from cls.iri_links(link)

    def execute(self, obj):
        if not isinstance(obj, str):
            raise TypeError('\'{}\' is not of type str.'.format(obj))

        find_all = re.findall('|'.join(
            '({})'.format(attr.pattern)
            for link in self.iri_links()
            for attr in link.__dict__.values()
            if isinstance(attr, type(re.compile('')))  # Can't import the actual type of a compiled re
        ), obj)

        if len(find_all) > 1:
            raise ValueError('\'{}\' contains multiple IRIs'.format(obj))

        final = (None, 0.0)
        for link in self.iri_links():
            hint = link.hint(obj)
            if hint and hint > final[1]:
                final = (link, hint)
            if hint == 1.0:
                break

        if not final[0]:
            if self._urn_fallback:
                urn = self.FALLBACK_FORMAT.format(source=Context()._config.label, id=urllib.parse.quote(obj))
                return URNLink().execute(urn)
            else:
                raise ValueError('\'{}\' could not be identified as an Identifier.'.format(obj))
        return final[0]().execute(obj)


class GuessAgentTypeLink(AbstractLink):
    """
    When executed on the name of an agent, guess the agent's type.
    """

    ORGANIZATION_KEYWORDS = (
        r'(^the\s|\sthe\s)',
        r'^[-A-Z]+$',
        'bureau',
        'council',
        'center',
        'foundation',
        'group',
        'inc',
        'society',
    )
    ORGANIZATION_RE = re.compile(r'\b({})\b'.format('|'.join(ORGANIZATION_KEYWORDS)), flags=re.I)

    INSTITUTION_KEYWORDS = (
        'college',
        'institute',
        'institution',
        'school',
        'university',
        'univ',
    )
    INSTITUTION_RE = re.compile(r'\b({})\b'.format('|'.join(INSTITUTION_KEYWORDS)), flags=re.I)

    def __init__(self, default=None):
        super(GuessAgentTypeLink, self).__init__()
        self._default = default

    def execute(self, obj):
        # TODO smarter guessing
        if self.INSTITUTION_RE.search(obj):
            return 'institution'
        if self.ORGANIZATION_RE.search(obj):
            return 'organization'
        return (self._default or 'person').lower()


class FilterLink(AbstractLink):

    def __init__(self, func):
        self._func = func
        super().__init__()

    def execute(self, obj):
        return list(filter(self._func, obj))


class UniqueLink(AbstractLink):

    def execute(self, obj):
        if not isinstance(obj, (list, tuple)):
            obj = (obj, )
        return list(set(obj))


class IntLink(AbstractLink):
    def execute(self, obj):
        return int(obj) if obj else None
