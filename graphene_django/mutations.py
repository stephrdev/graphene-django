from collections import OrderedDict

import graphene
from graphene.relay.mutation import ClientIDMutation
from graphene.types import Field, InputField
from graphene.types.mutation import MutationOptions as BaseMutationOptions
from graphene_django.forms.types import ErrorType

from .exceptions import PermissionDenied
from .permissions import GraphPermissions
from .registry import get_global_registry
from .utils import get_and_validate_global_id


class MutationPermissionsMixin:
    """
    Mixin for ObjectTypes to support permission checking.
    """
    permission_classes = None

    @classmethod
    def get_permission_classes(cls, info):
        return cls.permission_classes

    @classmethod
    def ensure_permission(cls, root, info, **data):
        for permission in cls.get_permission_classes(info) or []:
            if not permission(cls).has_mutation_permission(root, info, data):
                raise PermissionDenied

        return True


class MutationOptions(BaseMutationOptions):
    model = None
    registry = None
    node_type = None
    lookup_field = None


class BaseMutation(MutationPermissionsMixin, ClientIDMutation):
    """
    Base mutation with permission and optional model support. You should not use
    this class directly, always pick one of Create/Update/DeleteMutation instead.
    This is required for proper permission checking.

    If no input for lookup is defined, a graphene.ID is added if lookup_field
    is not False. (the default).
    """
    ok = graphene.Boolean()
    errors = graphene.List(
        ErrorType,
        description='May contain more than one error for same field.'
    )

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls, model=None, lookup_field=None, input_fields=None, _meta=None,
        registry=None, **options
    ):
        if not _meta:
            _meta = MutationOptions(cls)

        _meta.registry = registry or get_global_registry()

        if lookup_field is None:
            lookup_field = model._meta.pk.name if model else None

        _meta.model = model
        _meta.node_type = _meta.registry.get_type_for_model(model) if model else None
        _meta.lookup_field = lookup_field

        # Add lookup field for update and delete operations.
        if _meta.lookup_field and issubclass(cls, (UpdateMutation, DeleteMutation)):
            if not input_fields:
                input_fields = OrderedDict()
            if (
                _meta.lookup_field not in input_fields and
                not hasattr(getattr(cls, 'Input', None), 'id')
            ):
                input_fields[_meta.lookup_field] = graphene.ID(required=True)

        super().__init_subclass_with_meta__(
            _meta=_meta, input_fields=input_fields, **options)

    @classmethod
    def get_queryset(cls, info):
        assert cls._meta.model, 'Model for mutation is missing'
        return cls._meta.model.objects.all()

    @classmethod
    def get_object(cls, info, data):
        assert cls._meta.model, 'Model for mutation is missing'
        lookup_field = cls._meta.lookup_field

        if lookup_field not in data:
            raise ValueError('Lookup value missing')

        lookup_value = data[lookup_field]
        node_id = get_and_validate_global_id(cls._meta.node_type, lookup_value)

        return cls.get_queryset(info).get(**{lookup_field: node_id})

    @classmethod
    def mutate_and_get_payload(cls, root, info, **data):
        cls.ensure_permission(root, info, **data)
        return cls.perform_mutate(root, info, **data)

    @classmethod
    def perform_mutate(cls, root, info, **data):
        return cls(ok=False)


class CreateMutation(BaseMutation):
    """
    Mutation for create operations. Choose this class if your mutation will
    create new objects/data.

    Note: this class has no custom implementation compared to BaseMutation.
    The idea behind an extra class is to allow the permission system to decide
    which kind of operation happens.
    """
    class Meta:
        abstract = True


class UpdateMutation(BaseMutation):
    """
    Mutation for update operations. Choose this class if your mutation will
    update existing objects/data.

    Note: this class has no custom implementation compared to BaseMutation.
    The idea behind an extra class is to allow the permission system to decide
    which kind of operation happens.
    """
    class Meta:
        abstract = True


class DeleteMutation(BaseMutation):
    """
    Mutation for update operations. Choose this class if your mutation will
    update existing objects/data.

    Note: this class has no custom implementation compared to BaseMutation.
    The idea behind an extra class is to allow the permission system to decide
    which kind of operation happens.
    """
    class Meta:
        abstract = True
