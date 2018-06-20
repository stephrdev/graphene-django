class PartialUpdatesFormMixin:
    """
    Form class helper to allow partial updates in certain cases:
    * Partial updates are enabled
    * A previously saved model instance is available.
    """

    def __init__(self, *args, **kwargs):
        partial_updates = kwargs.pop('partial_updates', False)

        super().__init__(*args, **kwargs)

        if partial_updates and (not self.instance or not self.instance.pk):
            raise ValueError(
                '`partial_updates` is not available without a saved model instance.')

        if partial_updates and self.instance and self.instance.pk:
            # We need to in-direct this loop to prevent mutation of ordered dict
            # while looping over it. Therefore we go with a 2nd run.
            for field in [field for field in self.fields]:
                if field not in self.data:
                    # Remove fields if no data is submitted to prevent validation
                    # and storing data.
                    del self.fields[field]


class GraphFormMixin:
    """
    Mixin for all graphene mutation related forms.
    """
    class Meta:
        formfield_callback = graph_formfield_callback()
