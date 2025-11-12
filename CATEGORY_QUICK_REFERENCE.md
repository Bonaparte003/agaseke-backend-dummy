# Category System - Quick Reference

## Admin Dashboard

### Create Category
```
/admin/ → Categories → Add Category
- Name: Electronics
- Slug: electronics (auto-generated)
- Description: Electronic devices...
- Upload Image: [Select file]
- Is Active: ✓
- Display Order: 1
```

---

## API Endpoints

### Get All Categories
```http
GET /auth/v1/categories/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {
        "id": 1,
        "name": "Electronics",
        "slug": "electronics",
        "description": "...",
        "category_image": "/media/categories/electronics.png",
        "product_count": 24,
        "display_order": 1
      }
    ]
  }
}
```

---

### Create Product with Category
```http
POST /auth/v1/posts/
Content-Type: multipart/form-data
Authorization: Bearer <token>

title: iPhone 15
description: Latest iPhone
price: 999.99
category: 1                    # Use category ID
# OR
category: electronics          # Use category slug
main_image: [file]
inventory: 10
```

---

### Filter Products by Category
```http
GET /auth/v1/dashboard/?category=1
# OR
GET /auth/v1/dashboard/?category=electronics
```

---

### Update Product Category
```http
PUT /auth/v1/posts/<post_id>/edit/
Content-Type: multipart/form-data
Authorization: Bearer <token>

category: 2                    # Update to category ID 2
# OR
category: books-media          # Update to Books & Media
```

---

## Response Format Changes

### Product Category (New)
```json
{
  "category": {
    "id": 1,
    "name": "Electronics",
    "slug": "electronics",
    "category_image": "/media/categories/electronics.png"
  }
}
```

### Product Category (Old - Deprecated)
```json
{
  "category": "electronics",
  "category_display": "Electronics"
}
```

---

## Python Usage

### Import
```python
from posts.models import Category, Post
```

### Get All Active Categories
```python
categories = Category.objects.filter(is_active=True).order_by('display_order')
```

### Get Category by ID
```python
category = Category.objects.get(id=1, is_active=True)
```

### Get Category by Slug
```python
category = Category.objects.get(slug='electronics', is_active=True)
```

### Create Product with Category
```python
category = Category.objects.get(slug='electronics')
post = Post.objects.create(
    title='iPhone 15',
    description='Latest iPhone',
    price=999.99,
    category=category,  # ForeignKey relationship
    inventory=10,
    user=user,
    image=image_file
)
```

### Filter Products by Category
```python
# By category object
electronics = Category.objects.get(slug='electronics')
products = Post.objects.filter(category=electronics)

# By category ID
products = Post.objects.filter(category__id=1)

# By category slug
products = Post.objects.filter(category__slug='electronics')
```

### Get Product Count per Category
```python
category = Category.objects.get(slug='electronics')
count = category.product_count()  # Method on Category model
# OR
count = category.posts.filter(inventory__gt=0).count()
```

---

## Common Patterns

### Accept Category ID or Slug
```python
def get_category_from_input(category_input):
    """Accept either category ID or slug"""
    if not category_input:
        return None
    
    try:
        # Try as ID first
        category_id = int(category_input)
        return Category.objects.get(id=category_id, is_active=True)
    except (ValueError, Category.DoesNotExist):
        # Try as slug
        try:
            return Category.objects.get(slug=category_input, is_active=True)
        except Category.DoesNotExist:
            return None
```

### Serialize Category
```python
def serialize_category(category):
    """Serialize category for API response"""
    if not category:
        return None
    
    return {
        'id': category.id,
        'name': category.name,
        'slug': category.slug,
        'category_image': category.category_image.url if category.category_image else None
    }
```

---

## Migration Status

✅ All existing products migrated  
✅ Old category choices mapped to new Category objects  
✅ No data loss  

**Mapping:**
- `electronics` → Electronics (ID: 1, slug: electronics)
- `books_media` → Books & Media (ID: 2, slug: books-media)
- `home_kitchen` → Home & Kitchen (ID: 3, slug: home-kitchen)
- `beauty_care` → Beauty & Personal Care (ID: 4, slug: beauty-care)
- `software_services` → Software & Services (ID: 5, slug: software-services)
- `health_fitness` → Health & Fitness (ID: 6, slug: health-fitness)
- `other` → Other (ID: 7, slug: other)

---

## Best Practices

1. **Always check `is_active=True`** when querying categories
2. **Accept both ID and slug** in API endpoints for flexibility
3. **Use `select_related('category')`** when fetching posts to avoid N+1 queries
4. **Validate category exists** before assigning to products
5. **Use slug for URLs**, ID for internal references
6. **Provide helpful error messages** when category not found

---

## Troubleshooting

**Category not showing in API?**
- Check `is_active=True` in admin

**Image not displaying?**
- Verify `MEDIA_URL` and `MEDIA_ROOT` in settings
- Check file was uploaded successfully

**Old category values not working?**
- They're deprecated but temporarily supported
- Update frontend to use new format (ID or slug)

**Can't find category by slug?**
- Slugs use hyphens: `books-media` not `books_media`
- Check exact slug in admin dashboard

---

## Key Files

- **Model:** `posts/models.py` → `Category`, `Post`
- **Admin:** `posts/admin.py` → `CategoryAdmin`
- **API:** `products/views.py` → `categories_api()`
- **Serializer:** `authentication/serializers_helpers.py` → `serialize_post()`
- **Migrations:** `posts/migrations/0003-0005_*.py`

---

## For More Details

See complete documentation:
- **`CATEGORY_MANAGEMENT_GUIDE.md`** - Full admin guide
- **`CHANGELOG_CATEGORY_UPDATE.md`** - Complete changelog
- **Django Admin** - `/admin/posts/category/`

