from django.conf import settings
from django.db import models

from share.models.fields import DateTimeAwareJSONField, ShareURLField
from share.models.validators import JSONLDValidator
from share.util import BaseJSONAPIMeta, rdfutil
from share.util.sharev2_to_rdf import sharev2_to_rdf


__all__ = ('NormalizedData',)


# TODO: rename to ResourceDescription
class NormalizedData(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    raw = models.ForeignKey('RawDatum', null=True, on_delete=models.CASCADE)
    data = DateTimeAwareJSONField(null=True, validators=[JSONLDValidator(), ])
    source = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tasks = models.ManyToManyField('CeleryTaskResult')

    resource_identifier = ShareURLField(blank=True, null=True)
    serialized_rdfgraph = models.BinaryField(null=True)  # alternate/replacement for `data` field
    _RDF_FORMAT = 'turtle'  # passed as `format` to rdflib.Graph.parse and .serialize

    def convert_to_rdf(self):
        if self.data is None:
            return None
        (focus_uri, rdfgraph) = sharev2_to_rdf(self.data)
        self.set_rdfgraph(rdfgraph)
        self.resource_identifier = focus_uri
        if self.id:
            self.save()
        return rdfgraph

    def get_rdfgraph(self, convert=False):
        if (self.serialized_rdfgraph is None) or (self.resource_identifier is None):
            if convert:
                return self.convert_to_rdf()
            else:
                return None
        return (
            rdfutil.contextualized_graph()
            .parse(format=self._RDF_FORMAT, data=self.serialized_rdfgraph)
        )

    def set_rdfgraph(self, rdfgraph):
        assert self.serialized_rdfgraph is None
        self.serialized_rdfgraph = rdfgraph.serialize(format=self._RDF_FORMAT)

    class JSONAPIMeta(BaseJSONAPIMeta):
        pass

    def __str__(self):
        return '<{}({}, {}, {})>'.format(self.__class__.__name__, self.id, self.source.get_short_name(), self.created_at)

    __repr__ = __str__
