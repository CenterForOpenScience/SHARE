from enum import Enum
from typing import Set, NamedTuple, Optional


RelationShape = Enum('RelationShape', ['MANY_TO_MANY', 'MANY_TO_ONE', 'ONE_TO_MANY'])
AttributeDataType = Enum('AttributeDataType', ['BOOLEAN', 'STRING', 'INTEGER', 'DATETIME', 'OBJECT'])
AttributeDataFormat = Enum('AttributeDataFormat', ['URI'])


class ShareV2SchemaType(NamedTuple):
    name: str
    concrete_type: str
    explicit_fields: Set[str]
    distance_from_concrete_type: int = 0


class ShareV2SchemaAttribute(NamedTuple):
    name: str
    data_type: AttributeDataType
    data_format: Optional[AttributeDataFormat]
    is_required: bool = False
    is_relation: bool = False


class ShareV2SchemaRelation(NamedTuple):
    name: str
    relation_shape: RelationShape
    related_concrete_type: str
    inverse_relation: str
    through_concrete_type: Optional[str] = None
    is_required: bool = False
    is_implicit: bool = False
    is_relation: bool = True
