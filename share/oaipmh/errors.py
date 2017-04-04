
class OAIError:
    def __init__(self, code, description):
        self.code = code
        self.description = description


class BadVerb(OAIError):
    def __init__(self, verbs=None):
        if not verbs:
            message = 'Missing OAI verb'
        elif len(verbs) > 1:
            message = 'Multiple OAI verbs: {}'.format(', '.join(verbs))
        else:
            message = 'Illegal OAI verb: {}'.format(verbs[0])
        super().__init__('badVerb', message)


class BadArgument(OAIError):
    def __init__(self, reason, name):
        super().__init__('badArgument', '{} argument: {}'.format(reason, name))


class BadFormat(OAIError):
    def __init__(self, prefix):
        super().__init__('cannotDisseminateFormat', 'Invalid metadataPrefix: {}'.format(prefix))


class BadRecordID(OAIError):
    def __init__(self, identifier):
        super().__init__('idDoesNotExist', 'Invalid record identifier: {}'.format(identifier))


class BadResumptionToken(OAIError):
    def __init__(self, token):
        super().__init__('badResumptionToken', 'Invalid or expired resumption token: {}'.format(token))


class NoResults(OAIError):
    def __init__(self):
        super().__init__('noRecordsMatch', 'No records match that query')
