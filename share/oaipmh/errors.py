
class OAIError:
    def __init__(self, code, description):
        self.code = code
        self.description = description


class BadVerb(OAIError):
    def __init__(self, verbs):
        super().__init__('badVerb', 'Illegal OAI verb: {}'.format(', '.join(verbs)))


class BadArgument(OAIError):
    def __init__(self, reason, name):
        super().__init__('badArgument', '{} argument: {}'.format(reason, name))
