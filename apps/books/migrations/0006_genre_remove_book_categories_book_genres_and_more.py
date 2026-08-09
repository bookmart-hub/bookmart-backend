# Custom migration: Rename Category → Genre (preserves data)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0005_review'),
    ]

    operations = [
        # 1. Rename the model table: Category → Genre
        migrations.RenameModel(
            old_name='Category',
            new_name='Genre',
        ),
        # 2. Rename the M2M field on Book: categories → genres
        migrations.RenameField(
            model_name='book',
            old_name='categories',
            new_name='genres',
        ),
        # 3. Update Meta options to reflect the new model name
        migrations.AlterModelOptions(
            name='genre',
            options={'ordering': ['name'], 'verbose_name_plural': 'Genres'},
        ),
        # 4. Update subtitle help_text to reference Genre instead of Category
        migrations.AlterField(
            model_name='genre',
            name='subtitle',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Genre subtitle/tagline e.g. 'Prepare to Succeed'",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name='genre',
            name='icon',
            field=models.CharField(
                blank=True,
                help_text="Emoji character or Lucide icon string lookup key (e.g., '🚀')",
                max_length=50,
            ),
        ),
    ]
