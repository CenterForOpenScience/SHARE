from share.models.validators import JSONLDValidator
from share.regulate import BaseValidationStep


class JSONLDValidatorStep(BaseValidationStep):
    def validate_graph(self, graph):
        JSONLDValidator()({'@graph': graph.to_jsonld()})
