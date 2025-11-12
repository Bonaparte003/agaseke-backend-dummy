# Manual migration to remove old_category field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0004_populate_categories_and_add_fk"),
    ]

    operations = [
        # Remove the old_category field
        migrations.RemoveField(
            model_name='post',
            name='old_category',
        ),
    ]

