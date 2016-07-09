import six
import ujson

from django import forms
from psycopg2.extras import Json
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core import exceptions, validators, checks
from django.db import models
from django.db.models.fields.related import resolve_relation
from django.utils.translation import ugettext_lazy as _
from share.models.validators import is_valid_uri


class DatetimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=ujson.dumps)
        return value

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=ujson.dumps)
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            ujson.dumps(value)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)


class ShareOneToOneField(models.OneToOneField):
    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **self.__kwargs)
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **self.__kwargs)

        version.contribute_to_class(cls, name + '_version', **kwargs)

        actual._share_version_field = version


class ShareForeignKey(models.ForeignKey):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **self.__kwargs)
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **self.__kwargs)

        version.contribute_to_class(cls, name + '_version', **kwargs)

        actual._share_version_field = version


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


class ShareManyToManyField(TypedManyToManyField):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)
        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **self.__kwargs)
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **self.__kwargs)
        version.contribute_to_class(cls, name[:-1] + '_versions', **kwargs)

        actual._share_version_field = version


class URIField(models.TextField):
    default_validators = [is_valid_uri, ]
    def __init__(self, *args, **kwargs):
        super(URIField, self).__init__(*args, **kwargs)


class ShareURLField(models.TextField):
    default_validators = [validators.URLValidator()]
    description = _("URL")

    def __init__(self, verbose_name=None, name=None, **kwargs):
        super(ShareURLField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ShareURLField, self).deconstruct()
        if kwargs.get("max_length") == 200:
            del kwargs['max_length']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause URL validation to be performed
        # twice.
        defaults = {
            'form_class': forms.URLField,
        }
        defaults.update(kwargs)
        return super(ShareURLField, self).formfield(**defaults)
