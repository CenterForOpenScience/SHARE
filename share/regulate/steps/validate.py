from django.core.exceptions import ValidationError

from share.models.validators import JSONLDValidator
from share.regulate.steps import ValidationStep


class JSONLDValidatorStep(ValidationStep):
    def validate_graph(self, graph):
        try:
            JSONLDValidator()({'@graph': graph.to_jsonld(in_edges=False)})
        except ValidationError as e:
            self.reject('Failed JSON-LD schema validation', exception=e)
