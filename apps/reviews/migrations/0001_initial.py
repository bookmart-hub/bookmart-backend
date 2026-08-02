from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("authentication", "0001_initial"),
        ("marketplace", "0003_remove_booklisting_images_booklistingimage"),
    ]
    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("review", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_written", to="authentication.user")),
                ("seller", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_received", to="authentication.user")),
                ("listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="marketplace.booklisting")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(fields=["reviewer", "listing"], name="unique_reviewer_listing"),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name="rating_range_1_5"),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(condition=~models.Q(reviewer=models.F("seller")), name="no_self_review"),
        ),
    ]
