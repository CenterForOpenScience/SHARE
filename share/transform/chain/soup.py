from bs4 import BeautifulSoup

from share.transform.chain.links import AbstractLink
from share.transform.chain import ChainTransformer


class SoupXMLDict:
    def __init__(self, data=None, soup=None):
        self.soup = soup or BeautifulSoup(data, 'lxml').html

    def __getitem__(self, key):
        if key[0] == '@':
            return self.soup[key[1:]]

        if key == '#text':
            return self.soup.get_text()

        res = self.soup.find_all(key)

        if not res:
            return None

        if isinstance(res, list):
            if len(res) > 1:
                return [type(self)(soup=el) for el in res]
            res = res[0]

        return type(self)(soup=res)

    def __getattr__(self, key):
        return self[key]

    def __repr__(self):
        return '{}(\'{}\')'.format(self.__class__.__name__, self.soup)


class SoupLink(AbstractLink):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        super().__init__()

    def execute(self, obj):
        if not obj:
            return None

        if isinstance(obj, list):
            res = [r for o in obj for r in o.soup.find_all(*self._args, **self._kwargs)]
        else:
            res = obj.soup.find_all(*self._args, **self._kwargs)

        if not res:
            return None

        if isinstance(res, list):
            if len(res) > 1:
                return [SoupXMLDict(soup=el) for el in res]
            res = res[0]
        return SoupXMLDict(soup=res)


def Soup(chain, *args, **kwargs):
    return chain + SoupLink(*args, **kwargs)


class SoupXMLTransformer(ChainTransformer):
    REMOVE_EMPTY = False

    def unwrap_data(self, data, **kwargs):
        return SoupXMLDict(data)
