from share.models import Contributor
from share.oaipmh.util import format_datetime

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


def strip_blank(d):
    return {k: [v for v in vlist if v] for k, vlist in d.items()}


class DublinCoreFormat(OAIFormat):
    prefix = 'oai_dc'
    schema = 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd'
    namespace = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    template = 'oaipmh/formats/oai_dc.xml'

    contributor_types = set(Contributor.get_types()) - set(['share.creator'])

    def work_context(self, work, view):
        agents = work.agent_relations.order_by('order_cited').values_list('type', 'cited_as')
        date = work.date_published or work.date_updated
        context = {
            'titles': [work.title],
            'descriptions': [work.description],
            'creators': [a[1] for a in agents if a[0] == 'share.creator'],
            'publishers': [a[1] for a in agents if a[0] == 'share.publisher'],
            'contributors': [a[1] for a in agents if a[0] in self.contributor_types],
            'subjects': work.subjects.values_list('name', flat=True),
            'dates': [format_datetime(date) if date else None],
            'types': [work._meta.model_name],
            # 'formats': [],
            'identifiers': work.identifiers.values_list('uri', flat=True),
            # 'sources': [],
            'languages': [work.language],
            'relations': [view.oai_identifier(w) for w in work.related_works.all()],
            # 'coverages': [],
            'rights': [work.rights, work.free_to_read_type],
        }
        return strip_blank(context)
