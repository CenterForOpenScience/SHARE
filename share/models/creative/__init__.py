from share.models.base import ShareObject
from share.models.creative.base import Preprint
from share.models.creative.base import AbstractCreativeWork


__fields = {
    field
    for klass in AbstractCreativeWork.__subclasses__() + [AbstractCreativeWork]
    for field in klass._django_fields
}

__field_map = {field.name: field for field in __fields}


class __Meta:
    db_table = 'creative_work'

assert len(__fields) == len(__field_map), 'Found conflicting field names amongst all CreateWork models'

CreativeWork = type('CreativeWork', (ShareObject, ), {**__field_map, 'Meta': __Meta, '__module__': __package__, '__qualname__': 'CreativeWork'})
