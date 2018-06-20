class GraphQLError(Exception):
    default_message = 'A server error occurred'
    default_code = 'error'

    def __init__(self, message=None, code=None, **kwargs):
        self.code = code or self.default_code
        self.error_data = kwargs
        super().__init__(message or self.default_message)


class PermissionDenied(GraphQLError):
    default_message = 'You\'re not allowed to perform this action'
    default_code = 'permissionDenied'


class ValidationError(GraphQLError):
    default_message = 'Provided data is invalid'
    default_code = 'validationError'
