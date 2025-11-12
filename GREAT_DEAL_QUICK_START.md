# Great Deal - Quick Start Guide

## ⚡ Quick Setup

### 1. Mark a Product as Great Deal (Admin)

1. Go to `/admin/posts/post/`
2. Edit any product
3. In the **Pricing** section:
   - Set **Price**: `749.99` (discounted price)
   - Check **Is Great Deal**: ✓
   - Set **Original Price**: `999.99` (regular price)
4. Save

**Result**: Product now shows as `-25% OFF` with `$250 savings`

---

### 2. Create Great Deal via API

**POST** `/auth/v1/posts/`

```bash
Authorization: Bearer <your_token>
Content-Type: multipart/form-data

title: Black Friday iPhone
description: Limited time offer!
price: 749.99
is_great_deal: true
original_price: 999.99
main_image: [file]
category: 1
inventory: 50
```

**Response**:
```json
{
  "success": true,
  "data": {
    "price": 749.99,
    "is_great_deal": true,
    "original_price": 999.99,
    "discount_percentage": 25.0,
    "savings_amount": 250.0
  }
}
```

---

### 3. Display in Frontend

```javascript
// React/JavaScript Example
{product.is_great_deal ? (
  <div className="pricing">
    <span className="sale-price">${product.price}</span>
    <span className="original-price strikethrough">
      ${product.original_price}
    </span>
    <span className="badge">
      -{product.discount_percentage}% OFF
    </span>
    <p>Save ${product.savings_amount}!</p>
  </div>
) : (
  <span className="price">${product.price}</span>
)}
```

---

## 📊 API Response Format

```json
{
  "id": 1,
  "title": "iPhone 15 Pro",
  "price": 749.99,
  "is_great_deal": true,
  "original_price": 999.99,
  "discount_percentage": 25.0,
  "savings_amount": 250.0,
  ...
}
```

---

## ✅ Validation

- ✅ `original_price` > `price` (required)
- ✅ Both prices must be positive
- ❌ Can't set `is_great_deal=true` without `original_price`

---

## 🎯 Common Operations

### End a Sale
```bash
PUT /auth/v1/posts/1/edit/
{
  "is_great_deal": false,
  "price": 999.99
}
```

### Change Discount
```bash
PUT /auth/v1/posts/1/edit/
{
  "price": 599.99,
  "original_price": 999.99
}
# Now -40% OFF instead of -25%
```

---

## 📖 Full Documentation

See **`GREAT_DEAL_FEATURE.md`** for complete details!

