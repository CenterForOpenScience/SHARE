import abc
import json

import xmltodict

from share.normalize.links import Context


# NOTE: Context is a thread local singleton
# It is assigned to ctx here just to keep a family interface
ctx = Context()


class Normalizer(metaclass=abc.ABCMeta):

    root_parser = None

    NAMESPACES = {
        'http://purl.org/dc/elements/1.1/': 'dc',
        'http://www.openarchives.org/OAI/2.0/': None,
        'http://www.openarchives.org/OAI/2.0/oai_dc/': None,
    }

    def __init__(self, app_config):
        self.config = app_config

    def do_normalize(self, data):
        parsed = self.unwrap_data(data)
        parser = self.get_root_parser()

        return parser(parsed).parse()

    def unwrap_data(self, data):
        if data.startswith('<'):
            return xmltodict.parse(data, process_namespaces=True, namespaces=self.NAMESPACES)
        else:
            return json.loads(data)

    def get_root_parser(self):
        if self.root_parser:
            return self.root_parser

        try:
            module = __import__(self.config.name + '.normalizer', fromlist=('Manuscript', ))
        except ImportError:
            raise ImportError('Unable to find parser definitions at {}'.format(self.config.name + '.normalizer'))

        from share.models import AbstractCreativeWork
        root_levels = [
            getattr(module, klass.__name__)
            for klass in
            AbstractCreativeWork.__subclasses__()
            if hasattr(module, klass.__name__)
        ]

        if not root_levels:
            raise ImportError('No root level parsers found. You may have to create one or manually specifiy a parser with the root_parser attribute')

        if len(root_levels) > 1:
            raise ImportError('Found root level parsers {!r}. If more than one is found a single parser must be specified via the root_parser attribute')

        return root_levels[0]

    def normalize(self, raw_data):
        ctx.clear()  # Just incase
        ctx._config = self.config
        # Parsed data will be loaded into ctx
        if not isinstance(raw_data, str):
            raw_data = raw_data.data
        self.do_normalize(raw_data)
        jsonld = ctx.jsonld
        ctx.clear()  # Clean up

        return jsonld
