from share.transform.chain import links as tools, ChainTransformer

from . import io_osf
from .io_osf_preprints import ThroughSubjects


class Preprint(io_osf.Project):
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Concat(tools.Static({'text': 'Social and behavioral sciences'}))
    )


class SocarxivTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
