# Manual migration to create Category model and prepare for data migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0002_initial"),
    ]

    operations = [
        # Step 1: Create Category model
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Category name (e.g., Electronics)",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="URL-friendly version (auto-generated)",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Optional category description"
                    ),
                ),
                (
                    "category_image",
                    models.ImageField(
                        blank=True,
                        help_text="Category icon/image for visual representation",
                        null=True,
                        upload_to="categories/",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, help_text="Show/hide category"),
                ),
                (
                    "display_order",
                    models.IntegerField(
                        default=0, help_text="Order in which categories are displayed"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["display_order", "name"],
            },
        ),
        # Step 2: Rename existing category field to old_category
        migrations.RenameField(
            model_name='post',
            old_name='category',
            new_name='old_category',
        ),
    ]

