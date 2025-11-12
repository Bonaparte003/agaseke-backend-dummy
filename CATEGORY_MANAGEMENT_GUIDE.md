# Category Management Guide

## Overview

The KoraQuest platform now uses a **database-driven Category system** instead of hardcoded choices. This allows admins to create, edit, and manage product categories with visual representation through the Django admin dashboard.

## What Changed?

### Before
- Categories were hardcoded as choices in the `Post` model
- No way to add new categories without code changes
- No visual representation for categories

### After
- Categories are stored in the database as a separate `Category` model
- Admins can create/edit/delete categories through the admin dashboard
- Each category can have a visual image (`category_image`)
- Categories can be activated/deactivated
- Display order can be customized

---

## Category Model Structure

```python
class Category(models.Model):
    name            # Category name (e.g., "Electronics")
    slug            # URL-friendly version (auto-generated, e.g., "electronics")
    description     # Optional category description
    category_image  # Image for visual representation
    is_active       # Show/hide category (True/False)
    display_order   # Order in which categories are displayed (lower = first)
    created_at      # When category was created
    updated_at      # When category was last modified
```

---

## Managing Categories in Admin Dashboard

### Access the Admin Dashboard

1. Navigate to: `http://your-domain.com/admin/`
2. Login with admin credentials
3. Click on **"Categories"** under the **POSTS** section

### Creating a New Category

1. Click **"Add Category"** button
2. Fill in the required fields:
   - **Name**: The display name (e.g., "Electronics", "Fashion")
   - **Slug**: Auto-generated from name, but can be customized (e.g., "electronics")
   - **Description**: Optional description of what belongs in this category
3. Upload a **Category Image** (optional but recommended)
   - Recommended size: 200x200px or larger (square format works best)
   - Formats: PNG, JPG, JPEG
4. Set **Is Active**: Check to make category visible to users
5. Set **Display Order**: Lower numbers appear first (e.g., 1, 2, 3...)
6. Click **"Save"**

### Editing an Existing Category

1. Click on the category name in the list
2. Update any fields you want to change
3. Click **"Save"**

### Quick Editing from List View

You can quickly edit the following fields directly from the category list:
- **Is Active**: Check/uncheck to activate/deactivate
- **Display Order**: Change the number to reorder categories

After making changes, scroll down and click **"Save"** at the bottom.

### Deactivating a Category

Instead of deleting categories (which could break existing product associations), you can deactivate them:

1. Uncheck the **"Is Active"** checkbox
2. Save the category

Deactivated categories:
- Won't appear in the categories API
- Won't be available when creating new products
- Existing products with this category will retain it (but category won't be visible in listings)

### Viewing Category Stats

In the admin list view, you can see:
- **Image Preview**: Thumbnail of the category image
- **Product Count**: Number of active products in this category
- **Is Active**: Whether the category is visible
- **Display Order**: The order in which it appears

---

## Default Categories

The system comes with 7 pre-populated categories:

1. **Electronics** - Electronic devices, gadgets, computers, and accessories
2. **Books & Media** - Books, magazines, movies, music, and digital media
3. **Home & Kitchen** - Home appliances, furniture, kitchenware, and decor
4. **Beauty & Personal Care** - Cosmetics, skincare, haircare, and personal care products
5. **Software & Services** - Software applications, digital services, and subscriptions
6. **Health & Fitness** - Health products, fitness equipment, and wellness items
7. **Other** - Miscellaneous products (display_order: 999, appears last)

---

## API Integration

### Categories API Endpoint

**GET** `/auth/v1/categories/`

**Response:**
```json
{
  "success": true,
  "message": "Categories retrieved successfully",
  "data": {
    "categories": [
      {
        "id": 1,
        "name": "Electronics",
        "slug": "electronics",
        "description": "Electronic devices, gadgets, computers, and accessories",
        "category_image": "/media/categories/electronics_icon.png",
        "product_count": 24,
        "display_order": 1
      },
      {
        "id": 2,
        "name": "Books & Media",
        "slug": "books-media",
        "description": "Books, magazines, movies, music, and digital media",
        "category_image": "/media/categories/books_icon.png",
        "product_count": 15,
        "display_order": 2
      }
      // ... more categories
    ],
    "total_categories": 7
  }
}
```

### Creating Products with Categories

**POST** `/auth/v1/posts/`

**Request (multipart/form-data):**
```
title: iPhone 15 Pro
description: Latest iPhone with amazing features
price: 999.99
main_image: [file]
category: 1              // Can use category ID
inventory: 10
```

OR

```
category: electronics    // Can use category slug
```

Both the category ID and slug are accepted.

### Filtering Products by Category

**GET** `/auth/v1/dashboard/?category=1`

OR

**GET** `/auth/v1/dashboard/?category=electronics`

---

## Post Response Format

When fetching posts/products, the category is now an object instead of a string:

```json
{
  "id": 1,
  "title": "iPhone 15 Pro",
  "description": "Latest iPhone",
  "price": 999.99,
  "category": {
    "id": 1,
    "name": "Electronics",
    "slug": "electronics",
    "category_image": "/media/categories/electronics_icon.png"
  },
  "inventory": 10,
  // ... other fields
}
```

**Before (deprecated):**
```json
{
  "category": "electronics",
  "category_display": "Electronics"
}
```

---

## Best Practices

### Naming Categories
- Use clear, descriptive names
- Keep names concise (2-3 words maximum)
- Use title case (e.g., "Home & Kitchen" not "home & kitchen")

### Category Images
- Use consistent image sizes (200x200px recommended)
- Use simple, recognizable icons
- Use transparent backgrounds (PNG) for best results
- Ensure images are web-optimized (keep file size under 100KB)

### Display Order
- Reserve numbers 1-100 for main categories
- Use 100+ for subcategories (if you add them later)
- Use 999 for "Other" or miscellaneous categories
- Leave gaps (1, 5, 10, 15...) to allow easy reordering

### Category Slugs
- Auto-generated from name
- Use lowercase with hyphens
- Examples: `electronics`, `books-media`, `home-kitchen`
- Can be manually edited if needed

---

## Troubleshooting

### Category image not showing?

1. Check that `MEDIA_URL` and `MEDIA_ROOT` are configured in `settings.py`
2. Ensure the image was uploaded successfully
3. Verify file permissions on the `media/categories/` directory

### Products not appearing when filtering by category?

1. Ensure the category is **active** (`is_active=True`)
2. Check that products actually have this category assigned
3. Verify you're using the correct category ID or slug in the filter

### Can't delete a category?

This is by design. If products are associated with a category:
- **Recommended**: Deactivate the category instead
- **Alternative**: First reassign all products to a different category, then delete

---

## Migration Information

The system automatically migrated existing products from the old category system to the new one:

- Old: `category = "electronics"` (CharField)
- New: `category = ForeignKey(Category)` (Relation to Category model)

Mapping:
- `electronics` → Electronics (slug: `electronics`)
- `books_media` → Books & Media (slug: `books-media`)
- `home_kitchen` → Home & Kitchen (slug: `home-kitchen`)
- `beauty_care` → Beauty & Personal Care (slug: `beauty-care`)
- `software_services` → Software & Services (slug: `software-services`)
- `health_fitness` → Health & Fitness (slug: `health-fitness`)
- `other` → Other (slug: `other`)

---

## Admin Dashboard Features

The Category admin interface includes:

✅ **List View Features:**
- Image preview thumbnails
- Product count for each category
- Quick edit for `is_active` and `display_order`
- Search by name and description
- Filter by active status and creation date

✅ **Edit View Features:**
- Organized fieldsets (Basic Info, Visual, Settings)
- Auto-slug generation from name
- Helpful descriptions for each field
- Image upload with preview

✅ **Advanced Features:**
- Searchable dropdown when assigning categories to products
- Ordering by display_order and name
- Product count method shows how many active products use this category

---

## Summary

The new Category system provides:
- ✨ **Flexibility**: Add/edit categories without code changes
- 🎨 **Visual Representation**: Category images for better UX
- 🎯 **Control**: Activate/deactivate categories as needed
- 📊 **Insights**: See product counts per category
- 🔄 **Order Management**: Customize category display order
- 🚀 **API-Friendly**: Full support in all API endpoints

All changes are backward-compatible and seamlessly integrated with existing products!

