from share.transform.base import BaseTransformer
from share.transform.chain.links import Context, IRILink

# NOTE: Context is a thread local singleton
# It is assigned to ctx here just to keep a family interface
ctx = Context()


class ChainTransformer(BaseTransformer):
    root_parser = None

    @property
    def allowed_roots(self):
        from share.models import AbstractCreativeWork
        return set(t.__name__ for t in AbstractCreativeWork.get_type_classes())

    def do_transform(self, data):
        # Parsed data will be loaded into ctx
        ctx.clear()  # Just in case
        ctx._config = self.config

        parsed = self.unwrap_data(data)
        self.remove_empty_values(parsed)
        parser = self.get_root_parser()

        root_ref = parser(parsed).parse()
        jsonld = ctx.jsonld
        ctx.clear()  # Clean up
        return jsonld, root_ref

    def unwrap_data(self, data):
        if data.startswith('<'):
            return xmltodict.parse(data, process_namespaces=True, namespaces=self.namespaces)
        else:
            return json.loads(data, object_pairs_hook=OrderedDict)

    def get_root_parser(self):
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
