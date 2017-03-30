from share.oaipmh import errors as oai_errors


class OAIVerb:
    def __init__(self, name, required=set(), optional=set(), exclusive=None):
        self.name = name
        self.required = required
        self.optional = optional
        self.exclusive = exclusive

    @classmethod
    def validate(cls, **kwargs):
        errors = []
        verbs = kwargs.pop('verb', None)
        if not verbs or len(verbs) > 1:
            errors.append(oai_errors.BadVerb(verbs))
        else:
            try:
                verb = next(v for v in VERBS if v.name == verbs[0])
            except StopIteration:
                errors.append(oai_errors.BadVerb(verbs))
        if errors:
            return None, errors

        keys = set(kwargs.keys())

        illegal = keys - verb.required - verb.optional - set([verb.exclusive])
        for arg in illegal:
            errors.append(oai_errors.BadArgument('Illegal', arg))

        repeated = [k for k, v in kwargs.items() if len(v) > 1]
        for arg in repeated:
            errors.append(oai_errors.BadArgument('Repeated', arg))

        if verb.exclusive and verb.exclusive in keys:
            if (len(keys) > 1 or len(kwargs[verb.exclusive]) > 1):
                errors.append(oai_errors.BadArgument('Exclusive', verb.exclusive))
        else:
            missing = verb.required - keys
            for arg in missing:
                errors.append(oai_errors.BadArgument('Required', arg))

        return verb, errors


VERBS = {
    OAIVerb('Identify'),
    OAIVerb('ListMetadataFormats', optional={'identifier'}),
    OAIVerb('ListSets', exclusive='resumptionToken'),
    OAIVerb('ListIdentifiers', required={'metadataPrefix'}, optional={'from', 'until', 'set'}, exclusive='resumptionToken'),
    OAIVerb('ListRecords', required={'metadataPrefix'}, optional={'from', 'until', 'set'}, exclusive='resumptionToken'),
    OAIVerb('GetRecord', required={'identifier', 'metadataPrefix'}),
}
