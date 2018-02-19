import datetime as dt
import json
from decimal import Decimal
from functools import partial

from dateutil import parser
import jwe
from psycopg2.extras import Json
import six

from django import forms
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core import exceptions, validators, checks
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.fields.related import lazy_related_operation
from django.db.models.fields.related import resolve_relation
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.db.models.utils import make_model_tuple
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

from db.deletion import DATABASE_CASCADE


class DateTimeAwareJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, dt.datetime):
            return dict(type='encoded_datetime', value=o.isoformat())
        elif isinstance(o, dt.date):
            return dict(type='encoded_date', value=o.isoformat())
        elif isinstance(o, dt.time):
            return dict(type='encoded_time', value=o.isoformat())
        elif isinstance(o, Decimal):
            return dict(type='encoded_decimal', value=str(o))
        return super(DateTimeAwareJSONEncoder, self).default(o)


def decode_datetime_objects(nested_value):
    if isinstance(nested_value, list):
        return [decode_datetime_objects(item) for item in nested_value]
    elif isinstance(nested_value, dict):
        for key, value in nested_value.items():
            if isinstance(value, dict) and 'type' in value.keys():
                if value['type'] == 'encoded_datetime':
                    nested_value[key] = parser.parse(value['value'])
                if value['type'] == 'encoded_date':
                    nested_value[key] = parser.parse(value['value']).date()
                if value['type'] == 'encoded_time':
                    nested_value[key] = parser.parse(value['value']).time()
                if value['type'] == 'encoded_decimal':
                    nested_value[key] = Decimal(value['value'])
            elif isinstance(value, dict):
                nested_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                nested_value[key] = decode_datetime_objects(value)
        return nested_value
    return nested_value


class DateTimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return value

    def to_python(self, value):
        if value is None:
            return None
        return super(DateTimeAwareJSONField, self).to_python(decode_datetime_objects(value))

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            json.dumps(value, cls=DateTimeAwareJSONEncoder)
        except TypeError:
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


DatetimeAwareJSONField = DateTimeAwareJSONField


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)


# typedmodels modifies _meta.get_fields() on typed subclasses to filter out
# fields that don't belong, based on the fields given in the model definition.
# Share related fields don't directly contribute to classes, they make
# instances of their base class that contribute instead. Keep track of these
# fields that do a Share field's job, so they'll show up in _meta.get_fields().
class ShareRelatedField:

    PRETENDING_TO_BE = None

    def __init__(self, *args, **kwargs):
        # Correct M2M fields
        if 'to' in kwargs and not args:
            args = args + (kwargs.pop('to'), )

        self._kwargs = kwargs
        self.__equivalent_fields = set()
        super().__init__(*args, **kwargs)

    def add_equivalent_fields(self, *fields):
        self.__equivalent_fields.update(fields)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.PRETENDING_TO_BE(self.remote_field.model, **self._get_kwargs(cls))
        actual.contribute_to_class(cls, name, **kwargs)

        if isinstance(self.remote_field.model, str):
            version_model = self.remote_field.model + 'Version'
        elif hasattr(self.remote_field.model, 'VersionModel'):
            version_model = self.remote_field.model.VersionModel
        else:
            return  # Not pointing at a ShareObject subclass

        version = self.PRETENDING_TO_BE(version_model, **self._get_kwargs(cls, version=True))

        suffix = '_version'
        if self.many_to_many:
            suffix += 's'
            name = name.rstrip('s')

        version.contribute_to_class(cls, name + suffix, **kwargs)

        actual._share_version_field = version
        self.add_equivalent_fields(actual, version)

    def _get_kwargs(self, cls, version=False):
        kwargs = {**self._kwargs}
        through_fields = kwargs.get('through_fields', None)

        if version:
            kwargs['db_index'] = False
            kwargs['editable'] = False
            kwargs['related_name'] = '+'

        if through_fields:
            kwargs['through_fields'] = (
                '{}_version'.format(through_fields[0]) if 'version' in cls._meta.model_name else through_fields[0],
                '{}_version'.format(through_fields[1]) if version else through_fields[1]
            )
        return kwargs

    def __eq__(self, other):
        if other in self.__equivalent_fields:
            return True
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()


class ShareOneToOneField(ShareRelatedField, models.OneToOneField):
    PRETENDING_TO_BE = models.OneToOneField

    def __init__(self, *args, **kwargs):
        # Default to delete cascade
        kwargs.setdefault('on_delete', DATABASE_CASCADE)
        super().__init__(*args, **kwargs)


class ShareForeignKey(ShareRelatedField, models.ForeignKey):
    PRETENDING_TO_BE = models.ForeignKey

    def __init__(self, *args, **kwargs):
        # Default to delete cascade
        kwargs.setdefault('on_delete', DATABASE_CASCADE)
        super().__init__(*args, **kwargs)


def create_many_to_many_intermediary_model(field, klass):
    from django.db import models

    def set_managed(model, related, through):
        through._meta.managed = model._meta.managed or related._meta.managed

    to_model = resolve_relation(klass, field.remote_field.model)
    name = '%s_%s' % (klass._meta.object_name, field.name)
    lazy_related_operation(set_managed, klass, to_model, name)

    to = make_model_tuple(to_model)[1]
    from_ = klass._meta.model_name
    if to == from_:
        to = 'to_%s' % to
        from_ = 'from_%s' % from_

    meta = type(str('Meta'), (object,), {
        'db_table': field._get_m2m_db_table(klass._meta),
        'auto_created': klass,
        'app_label': klass._meta.app_label,
        'db_tablespace': klass._meta.db_tablespace,
        'unique_together': (from_, to),
        'verbose_name': _('%(from)s-%(to)s relationship') % {'from': from_, 'to': to},
        'verbose_name_plural': _('%(from)s-%(to)s relationships') % {'from': from_, 'to': to},
        'apps': field.model._meta.apps,
    })
    # Construct and return the new class.
    return type(str(name), (models.Model,), {
        'Meta': meta,
        '__module__': klass.__module__,
        from_: models.ForeignKey(
            klass,
            related_name='%s+' % name,
            db_tablespace=field.db_tablespace,
            db_constraint=field.remote_field.db_constraint,
            on_delete=DATABASE_CASCADE,
        ),
        to: models.ForeignKey(
            to_model,
            related_name='%s+' % name,
            db_tablespace=field.db_tablespace,
            db_constraint=field.remote_field.db_constraint,
            on_delete=DATABASE_CASCADE,
        )
    })


class TypedManyToManyField(models.ManyToManyField):

    def _check_relationship_model(self, from_model=None, **kwargs):
        if hasattr(self.remote_field.through, '_meta'):
            qualified_model_name = "%s.%s" % (
                self.remote_field.through._meta.app_label, self.remote_field.through.__name__)
        else:
            qualified_model_name = self.remote_field.through

        errors = []

        if self.remote_field.through not in self.opts.apps.get_models(include_auto_created=True):
            # The relationship model is not installed.
            errors.append(
                checks.Error(
                    ("Field specifies a many-to-many relation through model "
                     "'%s', which has not been installed.") %
                    qualified_model_name,
                    hint=None,
                    obj=self,
                    id='fields.E331',
                )
            )

        else:

            assert from_model is not None, (
                "ManyToManyField with intermediate "
                "tables cannot be checked if you don't pass the model "
                "where the field is attached to."
            )

            # Set some useful local variables
            to_model = resolve_relation(from_model, self.remote_field.model)
            from_model_name = from_model._meta.object_name
            if isinstance(to_model, six.string_types):
                to_model_name = to_model
            else:
                to_model_name = to_model._meta.object_name
            relationship_model_name = self.remote_field.through._meta.object_name
            self_referential = from_model == to_model

            # Check symmetrical attribute.
            if (self_referential and self.remote_field.symmetrical and
                    not self.remote_field.through._meta.auto_created):
                errors.append(
                    checks.Error(
                        'Many-to-many fields with intermediate tables must not be symmetrical.',
                        hint=None,
                        obj=self,
                        id='fields.E332',
                    )
                )

            # Count foreign keys in intermediate model
            if self_referential:
                seen_self = sum(from_model == getattr(field.remote_field, 'model', None)
                                for field in self.remote_field.through._meta.fields)

                if seen_self > 2 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than two foreign keys "
                             "to '%s', which is ambiguous. You must specify "
                             "which two foreign keys Django should use via the "
                             "through_fields keyword argument.") % (self, from_model_name),
                            hint=("Use through_fields to specify which two "
                                  "foreign keys Django should use."),
                            obj=self.remote_field.through,
                            id='fields.E333',
                        )
                    )

            else:
                # Count foreign keys in relationship model
                # HERE IS THE ACTUAL CHANGE
                # Look at models _meta.concrete_model to make typed models work
                seen_from = len([
                    field for field in self.remote_field.through._meta.fields
                    if hasattr(field.remote_field, 'model')
                    and from_model._meta.concrete_model == field.remote_field.model._meta.concrete_model
                ])
                seen_to = len([
                    field for field in self.remote_field.through._meta.fields
                    if hasattr(field.remote_field, 'model')
                    and to_model._meta.concrete_model == field.remote_field.model._meta.concrete_model
                ])

                if seen_from > 1 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than one foreign key "
                             "from '%s', which is ambiguous. You must specify "
                             "which foreign key Django should use via the "
                             "through_fields keyword argument.") % (self, from_model_name),
                            hint=('If you want to create a recursive relationship, '
                                  'use ForeignKey("self", symmetrical=False, '
                                  'through="%s").') % relationship_model_name,
                            obj=self,
                            id='fields.E334',
                        )
                    )

                if seen_to > 1 and not self.remote_field.through_fields:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it has more than one foreign key "
                             "to '%s', which is ambiguous. You must specify "
                             "which foreign key Django should use via the "
                             "through_fields keyword argument.") % (self, to_model_name),
                            hint=('If you want to create a recursive '
                                  'relationship, use ForeignKey("self", '
                                  'symmetrical=False, through="%s").') % relationship_model_name,
                            obj=self,
                            id='fields.E335',
                        )
                    )

                if seen_from == 0 or seen_to == 0:
                    errors.append(
                        checks.Error(
                            ("The model is used as an intermediate model by "
                             "'%s', but it does not have a foreign key to '%s' or '%s'.") % (
                                self, from_model_name, to_model_name
                            ),
                            hint=None,
                            obj=self.remote_field.through,
                            id='fields.E336',
                        )
                    )

        # Validate `through_fields`.
        if self.remote_field.through_fields is not None:
            # Validate that we're given an iterable of at least two items
            # and that none of them is "falsy".
            if not (len(self.remote_field.through_fields) >= 2 and
                    self.remote_field.through_fields[0] and self.remote_field.through_fields[1]):
                errors.append(
                    checks.Error(
                        ("Field specifies 'through_fields' but does not "
                         "provide the names of the two link fields that should be "
                         "used for the relation through model "
                         "'%s'.") % qualified_model_name,
                        hint=("Make sure you specify 'through_fields' as "
                              "through_fields=('field1', 'field2')"),
                        obj=self,
                        id='fields.E337',
                    )
                )

            # Validate the given through fields -- they should be actual
            # fields on the through model, and also be foreign keys to the
            # expected models.
            else:
                assert from_model is not None, (
                    "ManyToManyField with intermediate "
                    "tables cannot be checked if you don't pass the model "
                    "where the field is attached to."
                )

                source, through, target = from_model, self.remote_field.through, self.remote_field.model
                source_field_name, target_field_name = self.remote_field.through_fields[:2]

                for field_name, related_model in ((source_field_name, source),
                                                  (target_field_name, target)):

                    possible_field_names = []
                    for f in through._meta.fields:
                        if hasattr(f, 'remote_field') and getattr(f.remote_field, 'model', None) == related_model:
                            possible_field_names.append(f.name)
                    if possible_field_names:
                        hint = ("Did you mean one of the following foreign "
                                "keys to '%s': %s?") % (related_model._meta.object_name,
                                                        ', '.join(possible_field_names))
                    else:
                        hint = None

                    try:
                        field = through._meta.get_field(field_name)
                    except exceptions.FieldDoesNotExist:
                        errors.append(
                            checks.Error(
                                ("The intermediary model '%s' has no field '%s'.") % (
                                    qualified_model_name, field_name),
                                hint=hint,
                                obj=self,
                                id='fields.E338',
                            )
                        )
                    else:
                        if not (hasattr(field, 'remote_field') and
                                getattr(field.remote_field, 'model', None) == related_model):
                            errors.append(
                                checks.Error(
                                    "'%s.%s' is not a foreign key to '%s'." % (
                                        through._meta.object_name, field_name,
                                        related_model._meta.object_name),
                                    hint=hint,
                                    obj=self,
                                    id='fields.E339',
                                )
                            )

        return errors

    def _get_m2m_reverse_attr(self, related, attr):
        """
        Function that can be curried to provide the related accessor or DB
        column name for the m2m table.
        """
        cache_attr = '_m2m_reverse_%s_cache' % attr
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)
        found = False
        if self.remote_field.through_fields is not None:
            link_field_name = self.remote_field.through_fields[1]
        else:
            link_field_name = None
        for f in self.remote_field.through._meta.fields:
            # HERE IS THE ACTUAL CHANGE
            # Look at models _meta.concrete_model to make typed models work
            if f.is_relation and f.remote_field.model._meta.concrete_model == related.model._meta.concrete_model:
                if link_field_name is None and related.related_model._meta.concrete_model == related.model._meta.concrete_model:
                    # If this is an m2m-intermediate to self,
                    # the first foreign key you find will be
                    # the source column. Keep searching for
                    # the second foreign key.
                    if found:
                        setattr(self, cache_attr, getattr(f, attr))
                        break
                    else:
                        found = True
                elif link_field_name is None or link_field_name == f.name:
                    setattr(self, cache_attr, getattr(f, attr))
                    break
        return getattr(self, cache_attr)

    def contribute_to_class(self, cls, name, **kwargs):
            # To support multiple relations to self, it's useful to have a non-None
            # related name on symmetrical relations for internal reasons. The
            # concept doesn't make a lot of sense externally ("you want me to
            # specify *what* on my non-reversible relation?!"), so we set it up
            # automatically. The funky name reduces the chance of an accidental
            # clash.
            if self.remote_field.symmetrical and (
                    self.remote_field.model == "self" or self.remote_field.model == cls._meta.object_name):
                self.remote_field.related_name = "%s_rel_+" % name
            elif self.remote_field.is_hidden():
                # If the backwards relation is disabled, replace the original
                # related_name with one generated from the m2m field name. Django
                # still uses backwards relations internally and we need to avoid
                # clashes between multiple m2m fields with related_name == '+'.
                self.remote_field.related_name = "_%s_%s_+" % (cls.__name__.lower(), name)

            super(models.ManyToManyField, self).contribute_to_class(cls, name, **kwargs)

            # The intermediate m2m model is not auto created if:
            #  1) There is a manually specified intermediate, or
            #  2) The class owning the m2m field is abstract.
            #  3) The class owning the m2m field has been swapped out.
            if not cls._meta.abstract:
                if self.remote_field.through:
                    def resolve_through_model(_, model, field):
                        field.remote_field.through = model
                    lazy_related_operation(resolve_through_model, cls, self.remote_field.through, field=self)
                elif not cls._meta.swapped:
                    self.remote_field.through = create_many_to_many_intermediary_model(self, cls)

            # Add the descriptor for the m2m relation.
            setattr(cls, self.name, ManyToManyDescriptor(self.remote_field, reverse=False))

            # Set up the accessor for the m2m table name for the relation.
            self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)


class ShareManyToManyField(ShareRelatedField, TypedManyToManyField):
    PRETENDING_TO_BE = TypedManyToManyField


class URIField(models.TextField):
    def __init__(self, *args, **kwargs):
        super(URIField, self).__init__(*args, **kwargs)


class ShareURLField(models.TextField):
    default_validators = [validators.URLValidator()]
    description = _("URL")

    def __init__(self, verbose_name=None, name=None, **kwargs):
        super(ShareURLField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ShareURLField, self).deconstruct()
        kwargs.pop('max_length', None)
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause URL validation to be performed
        # twice.
        defaults = {
            'form_class': forms.URLField,
        }
        if self.null and self.unique:
            defaults['empty_value'] = None
        defaults.update(kwargs)
        return super(ShareURLField, self).formfield(**defaults)


class GenericRelationNoCascade(GenericRelation):
    @property
    def bulk_related_objects(self):
        # https://github.com/django/django/blob/master/django/db/models/deletion.py#L151
        # Disable django cascading deletes for this field
        raise AttributeError('This is a dirty hack')


class EncryptedJSONField(models.BinaryField):
    """
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    """
    prefix = b'jwe:::'

    def get_db_prep_value(self, input_json, **kwargs):
        if not input_json:
            return None

        input_json = self.prefix + jwe.encrypt(json.dumps(input_json).encode('utf-8'), settings.SENSITIVE_DATA_KEY)

        return input_json

    def to_python(self, output_json):
        if not output_json:
            return None

        output_json = json.loads(jwe.decrypt(bytes(output_json[len(self.prefix):]), settings.SENSITIVE_DATA_KEY).decode('utf-8'))

        return output_json

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)
