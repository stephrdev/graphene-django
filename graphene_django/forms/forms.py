import binascii

from django.core.exceptions import ValidationError
from django.forms import CharField, Field, MultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from graphene_django.registry import get_global_registry
from graphene_django.utils import get_and_validate_global_id
from graphql_relay import from_global_id


class GlobalIDFormField(Field):
    default_error_messages = {
        'invalid': _('Invalid ID specified.'),
    }

    def clean(self, value):
        if not value and not self.required:
            return None

        try:
            _type, _id = from_global_id(value)
        except (TypeError, ValueError, UnicodeDecodeError, binascii.Error):
            raise ValidationError(self.error_messages['invalid'])

        try:
            CharField().clean(_id)
            CharField().clean(_type)
        except ValidationError:
            raise ValidationError(self.error_messages['invalid'])

        return value


class GlobalIDMultipleChoiceField(MultipleChoiceField):
    default_error_messages = {
        'invalid_choice': _('One of the specified IDs was invalid (%(value)s).'),
        'invalid_list': _('Enter a list of values.'),
    }

    def valid_value(self, value):
        # Clean will raise a validation error if there is a problem
        GlobalIDFormField().clean(value)
        return True


class EnumFieldMixin:
    """
    Mixin for shared code of both EnumField and MultipleEnumField.
    The code stores the provided enum model and field target and extracts the
    choices of the target enum/model field.
    """
    empty_values = forms.Field.empty_values + ['NONE']

    def __init__(self, *args, **kwargs):
        self.enum = kwargs.pop('enum', None)
        if self.enum:
            kwargs['choices'] = getattr(self.enum, 'choices', [])
        else:
            self.enum_model = apps.get_model(kwargs.pop('enum_model'))
            self.enum_field = self.enum_model._meta.get_field(kwargs.pop('enum_field'))
            self.registry = kwargs.pop('registry', get_global_registry())
            kwargs['choices'] = self.enum_field.choices

        super().__init__(*args, **kwargs)

    def get_enum(self):
        if self.enum:
            return self.enum

        node_type = self.registry.get_type_for_model(self.enum_model)
        if node_type is None:
            raise ValueError('{} is not registered in given registry.'.format(self.enum_model))
        node_field = node_type._meta.fields[self.enum_field.name]
        return getattr(node_field._type, 'of_type', node_field._type)


class EnumField(EnumFieldMixin, forms.ChoiceField):
    """
    Subclass of forms.ChoiceField to accept some extra arguments for later field
    conversion.
    """
    pass


class MultipleEnumField(EnumFieldMixin, forms.MultipleChoiceField):
    """
    Subclass of forms.MultipleChoiceField to accept some extra arguments for
    later field conversion.
    """
    pass


class GlobalIdModelChoiceField(forms.ModelChoiceField):

    def __init__(self, *args, **kwargs):
        self.registry = kwargs.pop('registry', get_global_registry())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None

        try:
            value = get_and_validate_global_id(
                self.registry.get_type_for_model(self.queryset.model), value)
        except (TypeError, ValueError):
            pass

        return super().to_python(value)


class GlobalIdModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    def __init__(self, *args, **kwargs):
        self.registry = kwargs.pop('registry', get_global_registry())
        super().__init__(*args, **kwargs)

    def _check_values(self, value):
        try:
            value = frozenset(value)
        except TypeError:
            raise forms.ValidationError(self.error_messages['list'], code='list')

        node_type = self.registry.get_type_for_model(self.queryset.model)
        new_value = []
        for value_item in value:
            try:
                value_item = get_and_validate_global_id(node_type, value_item)
            except (TypeError, ValueError):
                pass

            new_value.append(value_item)

        return super()._check_values(new_value)
