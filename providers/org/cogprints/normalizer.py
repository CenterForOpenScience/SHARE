from share.normalize import Parser, Delegate, ctx, tools
from share.normalize.oai import OAINormalizer, OAICreativeWork


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Preprint(OAICreativeWork):
    schema = 'preprint'
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Subjects(ctx.record.metadata.dc['dc:subject'])
    )


class CogprintsNormalizer(OAINormalizer):
    root_parser = Preprint
