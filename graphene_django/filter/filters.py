import django_filters

from graphene_django.forms.forms import EnumField, MultipleEnumField


class EnumFilter(django_filters.ChoiceFilter):
    field_class = EnumField


class MultipleEnumFilter(django_filters.MultipleChoiceFilter):
    field_class = MultipleEnumField
