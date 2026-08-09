from apps.tags.models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify


def tag_item(item, tag_names):
    """
    Tags a model instance (e.g. Book or BookListing) with a list of string tags.
    """
    if not tag_names:
        return

    content_type = ContentType.objects.get_for_model(item)

    for name in tag_names:
        name_clean = name.strip()
        if not name_clean:
            continue

        slug = slugify(name_clean)
        if not slug:
            slug = "tag"

        # Get or create tag
        tag, _ = Tag.objects.get_or_create(
            slug=slug,
            defaults={"name": name_clean}
        )

        # Create generic tagged item relation if it doesn't exist
        TaggedItem.objects.get_or_create(
            tag=tag,
            content_type=content_type,
            object_id=item.id
        )
