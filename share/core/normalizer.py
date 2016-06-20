import abc
import json

from lxml import etree


class Normalizer(metaclass=abc.ABCMeta):

    root_parser = None

    def __init__(self, app_config):
        self.config = app_config

    def do_normalize(self, raw_data):
        if raw_data.data.startswith(b'<'):
            parsed = etree.fromstring(raw_data.data.decode())
        else:
            parsed = json.loads(raw_data.data.decode())

        if self.root_parser:
            parser = self.root_parser
        else:
            try:
                module = __import__(self.config.name + '.normalizer', fromlist=('Manuscript', ))
            except ImportError:
                raise ImportError('Unable to find normalizer definitions at {}'.format(self.config.name + '.normalizer'))

            try:
                parser = getattr(module, 'Manuscript')
            except AttributeError:
                raise ImportError('Unable to find Manuscript definition for {}'.format(self.config.name))

        return parser(parsed).parse()

    def normalize(self, raw_data):
        from share.parsers import ctx  # TODO Fix circular import

        ctx.clear()  # Just incase
        # Parsed data will be loaded into ctx
        self.do_normalize(raw_data)
        jsonld = ctx.jsonld
        ctx.clear()  # Clean up

        return jsonld
