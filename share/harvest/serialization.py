import json
import logging
import warnings

logger = logging.getLogger(__name__)


class RawDatumSerializer:
    """A deterministic serializer for harvested data.
    """

    def __init__(self, pretty):
        self.pretty = pretty

    def serialize(self, value):
        raise NotImplementedError()


class DictSerializer(RawDatumSerializer):

    def serialize(self, value):
        return json.dumps(value, sort_keys=True, indent=4 if self.pretty else None)


class DeprecatedDefaultSerializer(RawDatumSerializer):
    def __init__(self, pretty=False):
        super().__init__(pretty=pretty)
        self.warned = False
        self.dict_serializer = DictSerializer(pretty=pretty)
        warnings.warn('{!r} is deprecated. Use a serializer meant for the data returned'.format(self), DeprecationWarning)

    def serialize(self, data, pretty=False):
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            if not self.warned:
                self.warned = True
                warnings.warn(
                    '{!r}.encode_data got a bytes instance. '
                    'do_harvest should be returning str types as only the harvester will know how to properly encode the bytes '
                    'defaulting to decoding as utf-8'.format(self),
                    DeprecationWarning
                )
            return data.decode('utf-8')
        if isinstance(data, dict):
            return self.dict_serializer.serialize(data)
        raise Exception('Unable to properly encode data blob {!r}. Data should be a dict, bytes, or str objects.'.format(data))
