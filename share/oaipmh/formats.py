from share.models import Contributor

class OAIFormat:
    @property
    def prefix(self):
        raise NotImplementedError()

    @property
    def schema(self):
        raise NotImplementedError()

    @property
    def namespace(self):
        raise NotImplementedError()

    @property
    def template(self):
        raise NotImplementedError()

    def format_work(self, work):
        raise NotImplementedError()


class DublinCoreFormat(OAIFormat):
    prefix = 'oai_dc'
    schema = 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
    namespace = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    template = 'oaipmh/formats/oai_dc.xml'

    contributor_types = set(Contributor.get_types()) - set(['share.creator'])

    def work_context(self, work):
        agents = work.agent_relations.values_list('type', 'cited_as')
        date = work.date_published or work.date_updated
        return {
            'titles': [work.title] if work.title else [],
            'descriptions': [work.description] if work.description else [],
            'creators': [a[1] for a in agents if a[0] == 'share.creator'],
            'publishers': [a[1] for a in agents if a[0] == 'share.publisher'],
            'contributors': [a[1] for a in agents if a[0] not in self.contributor_types],
            'subjects': work.subjects.values_list('name', flat=True),
            'dates': [date] if date else [],
            'types': [work._meta.model_name],
            # 'formats': [],
            'identifiers': work.identifiers.values_list('uri', flat=True),
            # 'sources': [],
            'languages': [work.language] if work.language else [],
            'relations': 
        }
