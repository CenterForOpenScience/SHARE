from share.normalize import tools

from providers.io.osf import normalizer
from providers.io.osf.preprints.normalizer import ThroughSubjects


class Preprint(normalizer.Project):
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Concat(tools.Static({'text': 'Social and behavioral sciences'}))
    )
