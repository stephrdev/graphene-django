class GraphPermissions(object):
    """
    Base class for graphene/GraphQL permissions
    """
    node_type = None
    kwargs = None

    def __init__(self, node_type, **kwargs):
        self.node_type = node_type
        self.kwargs = kwargs

    def has_node_permission(cls, info, node_id):
        """
        Called when a node is directly accessed.
        """
        return False

    def has_mutation_permission(cls, root, info, data):
        """
        Will be called when a mutation should be executed.
        """
        return False

    def has_connection_permission(cls, info):
        """
        This check is called when a connection is resolved.
        """
        return False


class GraphReadWritePermissions(GraphPermissions):
    """
    Full read and write access. You have to limit access by yourself.
    """

    def has_node_permission(cls, info, node_id):
        return True

    def has_mutation_permission(cls, root, info, data):
        return True

    def has_connection_permission(cls, info):
        return True


class GraphReadonlyPermissions(GraphPermissions):
    """
    Full readonly access, no write access.
    """

    def has_node_permission(cls, info, node_id):
        return True

    def has_mutation_permission(cls, root, info, data):
        return False

    def has_connection_permission(cls, info):
        return True


class GraphModelPermissions(GraphPermissions):
    """
    Permissions backed by Django's Permission system.
    """
    perms_map = {
        'node': ['%(app_label)s.view_%(model_name)s'],
        'mutation_create': ['%(app_label)s.add_%(model_name)s'],
        'mutation_update': ['%(app_label)s.change_%(model_name)s'],
        'mutation_delete': ['%(app_label)s.delete_%(model_name)s'],
        'connection': ['%(app_label)s.view_%(model_name)s'],
    }

    def get_required_permissions(self, requested_access):
        return self.perms_map.get(requested_access, None)

    def has_permission(self, requested_access, info):
        required_permissions = self.get_required_permissions(requested_access)
        if required_permissions is None:
            return False

        if isinstance(required_permissions, str):
            required_permissions = (required_permissions,)

        model_meta = self.node_type._meta.model._meta
        placeholders = {
            'app_label': model_meta.app_label,
            'model_name': model_meta.model_name
        }
        required_permissions = [perm % placeholders for perm in required_permissions]

        return info.context.user.has_perms(required_permissions)

    def has_node_permission(self, info, node_id):
        return self.has_permission('node', info)

    def has_mutation_permission(self, root, info, data):
        # Needs refactor, we cannot import mutations directly, causes circular import.
        from . import mutations

        if issubclass(self.node_type, mutations.CreateMutation):
            return self.has_permission('mutation_create', info)

        if issubclass(self.node_type, mutations.DeleteMutation):
            return self.has_permission('mutation_delete', info)

        return self.has_permission('mutation_update', info)

    def has_connection_permission(self, info):
        return self.has_permission('connection', info)
