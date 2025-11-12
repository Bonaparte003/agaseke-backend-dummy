# Great Deal Feature Documentation

## Overview

The **Great Deal** feature allows vendors to mark products with special discounted pricing, showing customers how much they're saving. This helps track and display promotional items with clear pricing transparency.

---

## How It Works

### Concept

- **Normal Product**: `price` = regular selling price
- **Great Deal Product**: 
  - `price` = discounted/sale price (what customer pays)
  - `original_price` = regular price before discount
  - `is_great_deal` = `True`

### Automatic Calculations

The system automatically calculates:
- **Discount Percentage**: `((original_price - price) / original_price) * 100`
- **Savings Amount**: `original_price - price`

---

## Database Fields

### Post Model Fields

```python
# Current selling price (always required)
price = DecimalField(max_digits=10, decimal_places=2)

# Great Deal flag
is_great_deal = BooleanField(default=False)

# Original price before discount (required when is_great_deal=True)
original_price = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
```

### Helper Methods

```python
post.discount_percentage()  # Returns: 25.0 (for 25% off)
post.savings_amount()       # Returns: Decimal('50.00')
```

---

## Admin Dashboard

### Managing Great Deals

1. **Navigate to Products**: `/admin/posts/post/`
2. **Edit or Create a Product**
3. **In the "Pricing" section**:
   - Set **Price**: The discounted/sale price (e.g., $749.99)
   - Check **Is Great Deal**: ✓
   - Set **Original Price**: The regular price (e.g., $999.99)
4. **Save**

### Visual Indicators

In the admin list view, great deals show a red badge with the discount percentage:

```
Product Name    Price    [-25%]    Category    ...
```

### Filtering

- Filter products by **Is Great Deal** in the sidebar
- See which products are on sale at a glance

---

## API Integration

### Product Response Format

```json
{
  "id": 1,
  "title": "iPhone 15 Pro",
  "description": "Latest iPhone",
  "price": 749.99,
  "is_great_deal": true,
  "original_price": 999.99,
  "discount_percentage": 25.0,
  "savings_amount": 250.0,
  "category": {...},
  "inventory": 10,
  ...
}
```

### When NOT a Great Deal

```json
{
  "id": 2,
  "title": "Regular Product",
  "price": 99.99,
  "is_great_deal": false,
  "original_price": null,
  "discount_percentage": null,
  "savings_amount": null,
  ...
}
```

---

## Creating Products with Great Deals

### API Endpoint

**POST** `/auth/v1/posts/`

**Request (multipart/form-data):**

```
title: iPhone 15 Pro
description: Amazing phone on sale!
price: 749.99
is_great_deal: true
original_price: 999.99
main_image: [file]
category: 1
inventory: 10
```

**Response:**

```json
{
  "success": true,
  "message": "Product created successfully",
  "data": {
    "id": 1,
    "title": "iPhone 15 Pro",
    "price": 749.99,
    "is_great_deal": true,
    "original_price": 999.99,
    "discount_percentage": 25.0,
    "savings_amount": 250.0,
    ...
  }
}
```

---

## Updating Great Deals

### API Endpoint

**PUT/PATCH** `/auth/v1/posts/<post_id>/edit/`

**Request (multipart/form-data):**

```
is_great_deal: true
original_price: 999.99
price: 699.99
```

**This will update the product to show a 30% discount**

---

## Validation Rules

### 1. **Original Price Must Be Greater Than Sale Price**

If `is_great_deal=true` and `original_price <= price`:

```json
{
  "success": false,
  "message": "Invalid pricing",
  "errors": {
    "original_price": ["Original price must be greater than discounted price"]
  }
}
```

### 2. **Original Price Required for Great Deals**

When `is_great_deal=true`, you should provide `original_price` to show savings.

### 3. **Disabling Great Deal Clears Original Price**

When changing `is_great_deal` from `true` to `false`, the system automatically clears `original_price`.

---

## Frontend Display Examples

### Product Card

```html
<div class="product-card">
  <h3>iPhone 15 Pro</h3>
  
  <!-- Show both prices for great deals -->
  <div class="pricing">
    <span class="sale-price">$749.99</span>
    <span class="original-price strikethrough">$999.99</span>
    <span class="discount-badge">-25% OFF</span>
  </div>
  
  <p class="savings">Save $250.00!</p>
</div>
```

### Normal Product

```html
<div class="product-card">
  <h3>Regular Product</h3>
  
  <!-- Just show regular price -->
  <div class="pricing">
    <span class="price">$99.99</span>
  </div>
</div>
```

---

## Use Cases

### 1. **Flash Sales**

```
Original Price: $299.99
Sale Price: $199.99
Discount: 33% OFF
```

### 2. **Clearance Items**

```
Original Price: $149.99
Sale Price: $49.99
Discount: 67% OFF
```

### 3. **Seasonal Promotions**

```
Original Price: $799.99
Sale Price: $599.99
Discount: 25% OFF
```

### 4. **Bundle Deals**

```
Original Price: $1,299.99
Sale Price: $999.99
Discount: 23% OFF
```

---

## Filtering & Sorting

### Dashboard API

**Get All Great Deals:**

```http
GET /auth/v1/dashboard/?is_great_deal=true
```

**Sort by Discount (Frontend Implementation):**

```javascript
products
  .filter(p => p.is_great_deal)
  .sort((a, b) => b.discount_percentage - a.discount_percentage)
```

---

## Best Practices

### 1. **Accurate Pricing**

- Ensure `original_price` reflects the actual regular price
- Don't artificially inflate original prices

### 2. **Clear Communication**

- Show both prices clearly
- Display savings amount and percentage
- Use visual badges for quick recognition

### 3. **Limited Time Offers**

- Consider adding start/end dates for deals (future enhancement)
- Communicate urgency to customers

### 4. **Inventory Management**

- Update `is_great_deal` when sale ends
- Monitor inventory levels for popular deals

### 5. **Analytics**

- Track which great deals convert best
- Monitor sales velocity during promotions

---

## Frontend Implementation Example

### React/JavaScript Example

```javascript
const ProductCard = ({ product }) => {
  return (
    <div className="product-card">
      <h3>{product.title}</h3>
      <img src={product.image_url} alt={product.title} />
      
      <div className="pricing">
        {product.is_great_deal ? (
          <>
            <div className="sale-pricing">
              <span className="current-price">${product.price}</span>
              <span className="original-price">${product.original_price}</span>
            </div>
            <div className="discount-info">
              <span className="badge discount-badge">
                -{product.discount_percentage}% OFF
              </span>
              <span className="savings">
                Save ${product.savings_amount}
              </span>
            </div>
          </>
        ) : (
          <span className="regular-price">${product.price}</span>
        )}
      </div>
      
      <button>Add to Cart</button>
    </div>
  );
};
```

---

## Database Queries

### Get All Great Deals

```python
from posts.models import Post

great_deals = Post.objects.filter(
    is_great_deal=True,
    inventory__gt=0
).order_by('-created_at')
```

### Get Products by Discount Range

```python
# Get products with 20%+ discount
from django.db.models import F, DecimalField, ExpressionWrapper

products = Post.objects.filter(
    is_great_deal=True
).annotate(
    discount_pct=ExpressionWrapper(
        ((F('original_price') - F('price')) / F('original_price')) * 100,
        output_field=DecimalField()
    )
).filter(discount_pct__gte=20)
```

---

## Admin Dashboard Features

✅ **Visual Indicators**: Red discount badges in list view  
✅ **Quick Filtering**: Filter by great_deal status  
✅ **Organized Fields**: Dedicated "Pricing" fieldset  
✅ **Helpful Descriptions**: Clear instructions in admin  
✅ **Validation**: Server-side price validation  

---

## Migration Information

**Migration File**: `posts/migrations/0006_add_great_deal_fields.py`

**Changes**:
- Added `is_great_deal` field (default: False)
- Added `original_price` field (nullable)
- Updated `price` field help text

**Backward Compatible**: All existing products default to `is_great_deal=False`

---

## API Changelog

### New Fields in Product Responses

- `is_great_deal`: Boolean indicating if product is on sale
- `original_price`: Decimal showing regular price (null if not a deal)
- `discount_percentage`: Calculated discount % (null if not a deal)
- `savings_amount`: Calculated savings in currency (null if not a deal)

### Endpoints Updated

- ✅ `GET /auth/v1/dashboard/` - Returns great_deal info
- ✅ `GET /auth/v1/posts/<id>/` - Returns great_deal info
- ✅ `POST /auth/v1/posts/` - Accepts great_deal fields
- ✅ `PUT/PATCH /auth/v1/posts/<id>/edit/` - Updates great_deal fields
- ✅ `GET /auth/v1/purchases/` - Shows great_deal info in purchase history

---

## Example Scenarios

### Scenario 1: Create a Flash Sale Product

```bash
curl -X POST http://localhost:8000/auth/v1/posts/ \
  -H "Authorization: Bearer <token>" \
  -F "title=Flash Sale iPhone" \
  -F "description=Limited time offer!" \
  -F "price=699.99" \
  -F "is_great_deal=true" \
  -F "original_price=999.99" \
  -F "category=1" \
  -F "inventory=50" \
  -F "main_image=@iphone.jpg"
```

### Scenario 2: End a Sale (Convert to Regular Price)

```bash
curl -X PUT http://localhost:8000/auth/v1/posts/1/edit/ \
  -H "Authorization: Bearer <token>" \
  -F "is_great_deal=false" \
  -F "price=999.99"
```

### Scenario 3: Update Discount

```bash
curl -X PUT http://localhost:8000/auth/v1/posts/1/edit/ \
  -H "Authorization: Bearer <token>" \
  -F "price=649.99" \
  -F "original_price=999.99"
```
*This changes the discount from 30% to 35%*

---

## Summary

The Great Deal feature provides:

✨ **Transparency**: Clear pricing with original and sale prices  
📊 **Analytics**: Track discount effectiveness  
🎯 **Flexibility**: Easy to enable/disable deals  
💰 **Customer Value**: Show savings prominently  
🚀 **API-Ready**: Full integration in all endpoints  

All existing products remain unaffected and default to regular pricing!

