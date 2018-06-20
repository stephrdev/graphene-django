# from django import forms
from collections import OrderedDict

import graphene
from django.core.exceptions import ImproperlyConfigured
from graphene import Field, InputField
from graphene.relay.mutation import ClientIDMutation
from graphene.types.mutation import MutationOptions
# from graphene.types.inputobjecttype import (
#     InputObjectTypeOptions,
#     InputObjectType,
# )
from graphene.types.utils import yank_fields_from_attrs
from graphene_django.registry import get_global_registry

from .converter import convert_form_field
from graphene_django.mutations import (
    CreateMutation, MutationOptions, UpdateMutation, DeleteMutation)
from .types import ErrorType


def fields_for_form(form, only_fields, exclude_fields):
    fields = OrderedDict()
    for name, field in form.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = (
            name in exclude_fields  # or
            # name in already_created_fields
        )

        if is_not_in_only or is_excluded:
            continue

        fields[name] = convert_form_field(field)
    return fields


class FormMutationOptions(MutationOptions):
    form_class = None
    partial_updates = False


class FormMutationMixin:
    """
    Mutation mixin which supports Django form based mutations.

    The output fields contain a model node field if a model is defined in Meta.
    """

    @classmethod
    def __init_subclass_with_meta__(
        cls, model=None, form_class=None, only_fields=(), exclude_fields=(),
        partial_updates=False, registry=None, **options
    ):
        if not form_class:
            raise ImproperlyConfigured('Form class is missing')

        if not model:
            form_meta = getattr(form_class, 'Meta', None)
            if form_meta:
                model = getattr(form_meta, 'model', None)

        form = form_class()

        input_fields = fields_for_form(form, only_fields, exclude_fields)

        if partial_updates:
            for field in input_fields:
                input_fields[field].kwargs['required'] = False

        output_fields = fields_for_form(form, only_fields, exclude_fields)

        if model:
            node_type = registry.get_type_for_model(model)
            if node_type:
                output_fields[model._meta.model_name.lower()] = graphene.Field(node_type)

        _meta = FormMutationOptions(cls)
        _meta.form_class = form_class
        _meta.partial_updates = partial_updates
        _meta.fields = yank_fields_from_attrs(output_fields, _as=Field)

        input_fields = yank_fields_from_attrs(input_fields, _as=InputField)
        super().__init_subclass_with_meta__(
            _meta=_meta, model=model, input_fields=input_fields, registry=registry,
            **options
        )

    @classmethod
    def get_form_kwargs(cls, root, info, **data):
        kwargs = {'data': data}

        if info.context.FILES:
            kwargs['files'] = info.context.FILES

        if cls._meta.partial_updates:
            kwargs['partial_updates'] = True

        if cls._meta.model:
            instance = None
            if issubclass(cls, (UpdateMutation, DeleteMutation)):
                instance = cls.get_object(info, data)

            kwargs['instance'] = instance

        return kwargs

    @classmethod
    def perform_mutate(cls, root, info, **data):
        kwargs = cls.get_form_kwargs(root, info, **data)
        form = cls._meta.form_class(**kwargs)

        if form.is_valid():
            return cls.mutate_valid(form, info)

        return cls.mutate_invalid(form, info)

    @classmethod
    def save_instance(cls, form, info):
        """
        Hook to override save data
        """
        return form.save()

    @classmethod
    def mutate_valid(cls, form, info):
        obj = cls.save_instance(form, info)

        kwargs = {}
        for f, field in form.cleaned_data.items():
            if f in cls._meta.fields:
                kwargs[f] = field

        if cls._meta.model:
            kwargs[cls._meta.model._meta.model_name.lower()] = obj

        return cls(ok=True, **kwargs)

    @classmethod
    def mutate_invalid(cls, form, info):
        errors = [
            ErrorType(field=key, messages=value)
            for key, value in form.errors.items()
        ]
        return cls(ok=False, errors=errors)


class CreateFormMutation(FormMutationMixin, CreateMutation):
    """
    Form-based mutation to create objects/data.
    """
    class Meta:
        abstract = True


class UpdateFormMutation(FormMutationMixin, UpdateMutation):
    """
    Form-based mutation to update objects/data.
    """
    class Meta:
        abstract = True
