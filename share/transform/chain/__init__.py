from share.transform.chain.transformer import ChainTransformer
from share.transform.chain.links import Context


# Context singleton to be used for parser definitions
# Class SHOULD be thread safe
# Accessing subattribtues will result in a new copy of the context
# to avoid leaking data between chains
ctx = Context()
