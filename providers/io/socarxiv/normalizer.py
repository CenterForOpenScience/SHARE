from share.normalize import tools

from providers.io.engrxiv.normalizer import ThroughSubjects
from providers.io.engrxiv.normalizer import Preprint as EngrxivPreprint


class Preprint(EngrxivPreprint):
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Concat(tools.Static('Social and behavioral sciences'))
    )
