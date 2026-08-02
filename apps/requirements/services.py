from django.db import transaction

from apps.requirements.models import BookRequirement

# Optimised base queryset to avoid N+1 queries
REQUIREMENT_QUERYSET = BookRequirement.objects.select_related("user", "user__profile")


def create_requirement(*, user, book_title, preferred_condition, min_price=None, max_price=None, notes=""):
    """
    Create and return a new BookRequirement.

    All validation is handled in the serializer layer.
    """
    with transaction.atomic():
        requirement = BookRequirement.objects.create(
            user=user,
            book_title=book_title.strip(),
            preferred_condition=preferred_condition,
            min_price=min_price,
            max_price=max_price,
            notes=notes or "",
        )
    return requirement


def get_active_requirements():
    """Return queryset of all ACTIVE requirements, newest first."""
    return REQUIREMENT_QUERYSET.filter(status=BookRequirement.Status.ACTIVE).order_by("-created_at")


def get_requirements_for_user(*, user):
    """Return queryset of requirements for a specific user, newest first."""
    return REQUIREMENT_QUERYSET.filter(user=user).order_by("-created_at")


def get_requirement_by_id(*, requirement_id):
    """Return a single requirement with all related fields."""
    return REQUIREMENT_QUERYSET.get(pk=requirement_id)


def update_requirement(*, requirement, data):
    """
    Update a requirement's editable fields.
    Only the owner should call this (permission checked at view level).
    """
    update_fields = []

    if "book_title" in data:
        requirement.book_title = data["book_title"].strip()
        update_fields.append("book_title")
    if "preferred_condition" in data:
        requirement.preferred_condition = data["preferred_condition"]
        update_fields.append("preferred_condition")
    if "min_price" in data:
        requirement.min_price = data["min_price"]
        update_fields.append("min_price")
    if "max_price" in data:
        requirement.max_price = data["max_price"]
        update_fields.append("max_price")
    if "notes" in data:
        requirement.notes = data["notes"]
        update_fields.append("notes")
    if "status" in data:
        requirement.status = data["status"]
        update_fields.append("status")

    if update_fields:
        update_fields.append("updated_at")
        requirement.save(update_fields=update_fields)

    return requirement
