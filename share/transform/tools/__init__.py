from share.normalize.links import *  # noqa
from share.normalize.parsers import *  # noqa
from share.normalize.links import Context
from share.normalize.normalizer import Normalizer  # noqa


# Context singleton to be used for parser definitions
# Class SHOULD be thread safe
# Accessing subattribtues will result in a new copy of the context
# to avoid leaking data between chains
ctx = Context()
