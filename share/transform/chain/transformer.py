import re
from collections import OrderedDict

import json
import xmltodict

from share.transform.base import BaseTransformer
from share.transform.chain.links import Context


# NOTE: Context is a thread local singleton
# It is assigned to ctx here just to keep a family interface
ctx = Context()


class ChainTransformer(BaseTransformer):

    EMPTY_RE = re.compile(r'\s*(|none|empty)\s*', flags=re.I)

    NAMESPACES = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
        'http://www.loc.gov/mods/v3': 'mods',
    }

    REMOVE_EMPTY = True

    root_parser = None

    def __init__(self, *args, clean_up=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.clean_up = clean_up

    @property
    def allowed_roots(self):
        from share.models import AbstractCreativeWork
        return set(t.__name__ for t in AbstractCreativeWork.get_type_classes())

    def do_transform(self, data):
        # Parsed data will be loaded into ctx
        ctx.clear()  # Just in case
        ctx._config = self.config

        unwrapped = self.unwrap_data(data)
        if self.REMOVE_EMPTY:
            self.remove_empty_values(unwrapped)
        parser = self.get_root_parser(unwrapped)

        root_ref = parser(unwrapped).parse()
        jsonld = ctx.jsonld
        if self.clean_up:
            ctx.clear()
        return jsonld, root_ref

    def unwrap_data(self, data):
        if data.startswith('<'):
            return xmltodict.parse(data, process_namespaces=True, namespaces=self.kwargs.get('namespaces', self.NAMESPACES))
        else:
            return json.loads(data, object_pairs_hook=OrderedDict)

    def get_root_parser(self, unwrapped):
        if self.root_parser:
            return self.root_parser
        raise NotImplementedError('ChainTransformers must implement root_parser or get_root_parser')

    def remove_empty_values(self, parsed):
        if isinstance(parsed, dict):
            ret = OrderedDict()
            for k, v in parsed.items():
                if isinstance(v, (dict, list)):
                    v = self.remove_empty_values(v)
                if isinstance(v, str) and self.EMPTY_RE.fullmatch(v):
                    continue
                ret[k] = v
            return ret

        ret = []
        for v in parsed:
            if isinstance(v, (dict, list)):
                v = self.remove_empty_values(v)
            if isinstance(v, str) and self.EMPTY_RE.fullmatch(v):
                continue
            ret.append(v)
        return ret
