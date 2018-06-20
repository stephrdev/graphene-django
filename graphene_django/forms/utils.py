from django.utils.text import capfirst

from ..registry import get_global_registry
from .forms import EnumField, GlobalIdModelChoiceField, GlobalIdModelMultipleChoiceField


def graph_formfield_callback(registry=None):
    """
    Form helper to ensure that choice fields from models use the graph-optimized
    EnumFormField when converted to form fields.
    """
    if not registry:
        registry = get_global_registry()

    def formfield_callback(field, **kwargs):
        if isinstance(field, models.ForeignKey):
            kwargs['form_class'] = GlobalIdModelChoiceField
            kwargs['registry'] = registry

        elif isinstance(field, models.ManyToManyField):
            kwargs['form_class'] = GlobalIdModelMultipleChoiceField
            kwargs['registry'] = registry

        elif field.choices:
            defaults = {
                'required': not field.blank,
                'label': capfirst(field.verbose_name),
                'help_text': field.help_text,
                'registry': registry,
                'enum_model': '{}.{}'.format(
                    field.model._meta.app_label, field.model._meta.model_name),
                'enum_field': field.name
            }
            defaults.update(kwargs)
            return EnumField(**defaults)

        return field.formfield(**kwargs)

    return formfield_callback
