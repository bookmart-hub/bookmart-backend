from django_filters import rest_framework as filters

from apps.requirements.models import BookRequirement


class BookRequirementFilter(filters.FilterSet):
    """FilterSet for the public requirements list endpoint."""

    min_price = filters.NumberFilter(field_name="min_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="max_price", lookup_expr="lte")
    condition = filters.ChoiceFilter(field_name="preferred_condition", choices=BookRequirement.Condition.choices)
    status = filters.ChoiceFilter(field_name="status", choices=BookRequirement.Status.choices)

    class Meta:
        model = BookRequirement
        fields = ["condition", "status", "min_price", "max_price"]
