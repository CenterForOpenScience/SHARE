import json

from collections import OrderedDict

from share.legacy_normalize.transform import BaseTransformer


# The v2 Push API requires pushing already transformed data, so do nothing but parse JSON
class V2PushTransformer(BaseTransformer):
    VERSION = 1

    def do_transform(self, datum):
        parsed = json.loads(datum, object_pairs_hook=OrderedDict)
        return parsed, None
