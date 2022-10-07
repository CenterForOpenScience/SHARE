from share.legacy_normalize.transform.chain import ChainTransformer
from . import io_osf


class Preprint(io_osf.Project):
    pass


# TODO Could this just use the io.osf.preprints transformer instead?
class EngrxivTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
