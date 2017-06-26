import re
import logging
import collections

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
        self.types = collections.OrderedDict()

        logger.debug('Checking that %r is a valid XML Schema', self._tree)
        self._schema = etree.XMLSchema(self._tree)

        types = self._tree.xpath('/xs:schema/xs:complexType', namespaces=NS)
        logger.debug('Found %d complex types to be loaded as SchemaTypes', len(types))
        for typ in types:
            st = SchemaType(self, typ)
            self.types[st.name] = st
            logger.debug('Found %r', st)


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

    def to_django_model(self, constructor):
        attrs = {field.name.replace('-', '_'): field.to_django_field(constructor) for field in self.fields}

        attrs['__module__'] = constructor.module
        attrs['Meta'] = type('Meta', (), constructor.meta_for(self))

        return type(constructor.name_for(self), (constructor.base, ), attrs)

    def __repr__(self):
        return '<{}({})>'.format(type(self).__name__, self.name)


class SchemaField:

    is_relation = False

    @classmethod
    def match(self, tree):
        raise NotImplementedError()

    def __init__(self, _type, tree):
        self._tree = tree
        self._type = _type
        self.name = tree.get('name')
        self.required = tree.get('use') == 'required'

    def to_django_field(self, constructor):
        raise NotImplementedError()

    def _django_field_kwargs(self):
        return {
            'null': not self.required,
            **{
                attr.attrname.split('}')[-1]: int(attr) if attr.isnumeric()
                else {'true': True, 'false': False}.get(str(attr), str(attr))
                for attr in self._tree.xpath('@django:*', namespaces=NS)
            }
        }

    def __repr__(self):
        return '<{}({})>'.format(type(self).__name__, self.name)


class PrimativeField(SchemaField):

    TYPES = {
        'xs:string': models.TextField,
        'xs:boolean': models.NullBooleanField,
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

    def to_django_field(self, constructor):
        return self.TYPES[self._tree.get('type')](**self._django_field_kwargs())


class EnumField(SchemaField):

    @classmethod
    def match(self, tree):
        if not tree.xpath('./xs:simpleType/xs:restriction', namespaces=NS):
            return False
        return True

    def to_django_field(self, constructor):
        return models.TextField(
            choices=[
                (c.upper(), c)
                for c in self._tree.xpath('./xs:simpleType/xs:restriction/xs:enumeration/@value', namespaces=NS)
            ], **self._django_field_kwargs()
        )


class ForeignField(SchemaField):

    is_relation = True

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
        self._keyref = tree.xpath('//xs:keyref[@name = $name]', namespaces=NS, name=tree.get('name'))[0]
        # This is pretty fragile...
        self.related = self._keyref.attrib['refer'].split(':')[1].rstrip('ID')

    def to_django_field(self, constructor):
        return models.ForeignKey(constructor[self.related])
