# Manual migration to populate categories and add new category FK field

import django.db.models.deletion
from django.db import migrations, models


def create_initial_categories(apps, schema_editor):
    """Create initial categories from the old CATEGORY_CHOICES"""
    Category = apps.get_model('posts', 'Category')
    
    initial_categories = [
        {
            'name': 'Electronics',
            'slug': 'electronics',
            'description': 'Electronic devices, gadgets, computers, and accessories',
            'display_order': 1
        },
        {
            'name': 'Books & Media',
            'slug': 'books-media',
            'description': 'Books, magazines, movies, music, and digital media',
            'display_order': 2
        },
        {
            'name': 'Home & Kitchen',
            'slug': 'home-kitchen',
            'description': 'Home appliances, furniture, kitchenware, and decor',
            'display_order': 3
        },
        {
            'name': 'Beauty & Personal Care',
            'slug': 'beauty-care',
            'description': 'Cosmetics, skincare, haircare, and personal care products',
            'display_order': 4
        },
        {
            'name': 'Software & Services',
            'slug': 'software-services',
            'description': 'Software applications, digital services, and subscriptions',
            'display_order': 5
        },
        {
            'name': 'Health & Fitness',
            'slug': 'health-fitness',
            'description': 'Health products, fitness equipment, and wellness items',
            'display_order': 6
        },
        {
            'name': 'Other',
            'slug': 'other',
            'description': 'Miscellaneous products that don\'t fit other categories',
            'display_order': 999
        },
    ]
    
    for cat_data in initial_categories:
        Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )


def migrate_post_categories(apps, schema_editor):
    """Migrate existing post categories from old_category to new category FK"""
    Post = apps.get_model('posts', 'Post')
    Category = apps.get_model('posts', 'Category')
    
    # Mapping from old category choices to new category slugs
    category_mapping = {
        'electronics': 'electronics',
        'books_media': 'books-media',
        'home_kitchen': 'home-kitchen',
        'beauty_care': 'beauty-care',
        'software_services': 'software-services',
        'health_fitness': 'health-fitness',
        'other': 'other',
    }
    
    for post in Post.objects.all():
        old_cat = post.old_category
        if old_cat in category_mapping:
            slug = category_mapping[old_cat]
            try:
                category = Category.objects.get(slug=slug)
                post.category = category
                post.save()
            except Category.DoesNotExist:
                # Fallback to 'other' if category not found
                category = Category.objects.get(slug='other')
                post.category = category
                post.save()


def reverse_migration(apps, schema_editor):
    """Reverse the migration by copying category FK back to old_category"""
    Post = apps.get_model('posts', 'Post')
    Category = apps.get_model('posts', 'Category')
    
    # Reverse mapping from slug to old category choices
    reverse_mapping = {
        'electronics': 'electronics',
        'books-media': 'books_media',
        'home-kitchen': 'home_kitchen',
        'beauty-care': 'beauty_care',
        'software-services': 'software_services',
        'health-fitness': 'health_fitness',
        'other': 'other',
    }
    
    for post in Post.objects.all():
        if post.category:
            slug = post.category.slug
            if slug in reverse_mapping:
                post.old_category = reverse_mapping[slug]
                post.save()


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0003_create_category_model"),
    ]

    operations = [
        # Step 1: Populate Category table
        migrations.RunPython(create_initial_categories, migrations.RunPython.noop),
        
        # Step 2: Add new category FK field (nullable for now)
        migrations.AddField(
            model_name="post",
            name="category",
            field=models.ForeignKey(
                blank=True,
                help_text="Product category",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="posts",
                to="posts.category",
            ),
        ),
        
        # Step 3: Migrate data from old_category to new category FK
        migrations.RunPython(migrate_post_categories, reverse_migration),
    ]

