from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("authentication", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("type", models.CharField(choices=[("NEW_MESSAGE", "New Message"), ("NEW_MATCH", "New Match"), ("NEW_FAVORITE", "New Favorite"), ("LISTING_SOLD", "Listing Sold"), ("REPORT_UPDATED", "Report Updated"), ("REQUIREMENT_MATCH", "Requirement Match"), ("SYSTEM", "System")], db_index=True, default="SYSTEM", max_length=30)),
                ("reference_id", models.IntegerField(blank=True, null=True)),
                ("reference_type", models.CharField(blank=True, max_length=50, null=True)),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_notifications", to="authentication.user")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
