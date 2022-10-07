from share.legacy_normalize.transform.chain.exceptions import *  # noqa
from share.legacy_normalize.transform.chain.links import *  # noqa
from share.legacy_normalize.transform.chain.parsers import *  # noqa
from share.legacy_normalize.transform.chain.transformer import ChainTransformer  # noqa
from share.legacy_normalize.transform.chain.links import Context


# Context singleton to be used for parser definitions
# Class SHOULD be thread safe
# Accessing subattribtues will result in a new copy of the context
# to avoid leaking data between chains
ctx = Context()
