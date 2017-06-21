import logging
import datetime

from lxml import etree

from django.db import models


logger = logging.getLogger(__name__)

NAMESPACES = NS = {
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'share': 'http://share.osf.io/schema/v2/internal/schema.xsd',
    'django': 'https://docs.djangoproject.com/en/1.11/ref/models/fields/',
}


class Schema:

    @classmethod
    def load(cls, path, **kwargs):
        logger.debug('Opening %s', path)
        with open(path, 'r') as fobj:
            return cls(etree.parse(fobj), **kwargs)

    def __init__(self, tree):
        self._tree = tree
        self.types = []

        logger.debug('Checking that %r is a valid XML Schema', self._tree)
        self._schema = etree.XMLSchema(self._tree)

        types = self._tree.xpath('/xs:schema/xs:complexType', namespaces=NS)
        logger.debug('Found %d complex types to be loaded as SchemaTypes', len(types))
        for typ in types:
            self.types.append(SchemaType(self, typ))
            logger.debug('Found %r', self.types[-1])

    def to_django_models(self, name_tpl='{}', base=None):
        return [typ.to_django_model(name_tpl, base) for typ in self.types]


class SchemaType:

    def __init__(self, schema, tree):
        self.fields = []
        self._tree = tree
        self._schema = schema
        self.name = tree.get('name').rstrip('Type')

        for field in self._tree.xpath('./xs:sequence/xs:element', namespaces=NS):
            for field_type in SchemaField.__subclasses__():
                if field_type.match(field):
                    self.fields.append(field_type(self, field))
                    logger.debug('Found %r on %r', self.fields[-1], self)
                    break
            else:
                raise ValueError('Could not determine field type of {!r}'.format(field))

    def to_django_model(self, name_tpl='{}', base=None, **meta):
        attrs = {field.name: field.to_django_field() for field in self.fields}

        if meta:
            attrs['Meta'] = type('Meta', (), meta)

        attrs['__module__'] = __name__
        return type(name_tpl.format(self.name), (base or models.Model, ), attrs)

    def __repr__(self):
        return '<{}({})>'.format(type(self).__name__, self.name)


class SchemaField:

    @classmethod
    def match(self, tree):
        raise NotImplementedError()

    def __init__(self, _type, tree):
        self._tree = tree
        self._type = _type
        self.name = tree.get('name')
        self.required = tree.get('use') == 'required'

    def to_django_field(self):
        raise NotImplementedError()

    def _django_field_kwargs(self):
        # if self._tree.xpath('@django:index', namespaces=NS):
        #     import ipdb; ipdb.set_trace()

        return {
            'null': not self.required,
            **{
                attr.attrname.split('}')[-1]: int(attr) if attr.isnumeric()
                else {'true': True, 'false': False}.get(str(attr), str(attr))
                for attr in self._tree.xpath('@django:*', namespaces=NS)
            }
            # 'db_index': self._tree.xpath('@django:index', namespaces=NS) == 'true',
        }

    def __repr__(self):
        return '<{}({})>'.format(type(self).__name__, self.name)


class PrimativeField(SchemaField):

    TYPES = {
        'xs:string': models.TextField,
        'xs:boolean': models.BooleanField,
        'xs:date': models.DateField,
        'xs:time': models.TimeField,
        'xs:dateTime': models.DateTimeField,
        'xs:anyURI': models.URLField,  # TODO Replace with a better field
    }

    @classmethod
    def match(self, tree):
        if tree.get('type') not in self.TYPES:
            return False
        return True

    def to_django_field(self):
        return self.TYPES[self._tree.get('type')](**self._django_field_kwargs())


class EnumField(SchemaField):

    @classmethod
    def match(self, tree):
        if not tree.xpath('./xs:simpleType/xs:restriction', namespaces=NS):
            return False
        return True

    def to_django_field(self):
        return models.TextField(
            choices=[
                (c.upper(), c)
                for c in self._tree.xpath('./xs:simpleType/xs:restriction/xs:enumeration/@value', namespaces=NS)
            ], **self._django_field_kwargs()
        )


class ForeignField(SchemaField):

    @classmethod
    def match(self, tree):
        keyref = tree.xpath('//xs:keyref[@name = $name]', namespaces=NS, name=tree.get('name'))
        if not keyref:
            return False
        # foreign_type = field.xpath('//xs:complexType[@name = substring-after(//xs:element[@name = substring-after(//xs:key[@name = substring-after(//xs:keyref[@name = ./@name]/@refer, ":")]/xs:selector/@xpath, ":")]/@type, ":")]', namespaces=NS)[0]
        # logger.debug('Found foreign key %s of type %r', tree.get('name'), keyref)
        return True

    def __init__(self, _type, tree):
        super().__init__(_type, tree)
        self._keyref = tree.xpath('//xs:keyref[@name = $name]', namespaces=NS, name=tree.get('name'))

    def to_django_field(self):
        return models.ForeignKey('Foo')
