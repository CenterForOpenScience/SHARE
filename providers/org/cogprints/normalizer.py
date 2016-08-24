from share.normalize import Parser, Delegate, ctx, tools
from share.normalize.oai import OAINormalizer, OAIPreprint


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Preprint(OAIPreprint):

    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Try(ctx.record.metadata.dc['dc:subject'])
    )


class CogprintsNormalizer(OAINormalizer):
    root_parser = Preprint
