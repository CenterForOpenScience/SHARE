
class OAIFormat:

    def __init__(self, prefix, schema, namespace):
        self.prefix = prefix
        self.schema = schema
        self.namespace = namespace

    def format_work(self, work):
        raise NotImplementedError()


class DublinCoreFormat(OAIFormat):
    def __init__(self):
        super().__init__('oai_dc', 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd', 'http://www.openarchives.org/OAI/2.0/oai_dc/')
