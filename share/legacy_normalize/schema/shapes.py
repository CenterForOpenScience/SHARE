from enum import Enum
from typing import Set, NamedTuple, Optional, Tuple


RelationShape = Enum('RelationShape', ['MANY_TO_MANY', 'MANY_TO_ONE', 'ONE_TO_MANY'])
AttributeDataType = Enum('AttributeDataType', ['BOOLEAN', 'STRING', 'INTEGER', 'DATETIME', 'OBJECT'])
AttributeDataFormat = Enum('AttributeDataFormat', ['URI'])


class ShareV2SchemaType(NamedTuple):
    name: str
    concrete_type: str
    explicit_fields: Set[str]
    type_lineage: Tuple[str] = ()
    rdf_type: Optional(str) = None
    rdf_predicate: Optional(str) = None
    rdf_value_field: Optional(str) = None

    @property
    def distance_from_concrete_type(self):
        return len(self.type_lineage)


class ShareV2SchemaAttribute(NamedTuple):
    name: str
    data_type: AttributeDataType
    data_format: Optional[AttributeDataFormat]
    is_required: bool = False
    is_relation: bool = False
    rdf_predicate: Optional(str) = None


class ShareV2SchemaRelation(NamedTuple):
    name: str
    relation_shape: RelationShape
    related_concrete_type: str
    inverse_relation: str
    through_concrete_type: Optional[str] = None
    incoming_through_relation: Optional[str] = None
    outgoing_through_relation: Optional[str] = None
    is_required: bool = False
    is_implicit: bool = False
    is_relation: bool = True
    rdf_predicate: Optional(str) = None
