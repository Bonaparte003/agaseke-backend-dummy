# 👤 Normal User API Guide

Complete guide for all endpoints available to regular users (non-vendor, non-agaseke).

**Base URL:** `http://localhost:8000/auth/v1/`

---

## 🔐 Authentication Endpoints

### 1. Register Account
```http
POST /auth/v1/register/
```

**Request:** *(Single password field)*
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+250123456789"
}
```

**Validation:**
- Username: Min 3 chars, unique
- Email: Valid format, unique
- Password: Min 8 chars
- Phone: Min 10 digits

**Response:**
```json
{
  "success": true,
  "message": "Account created successfully. Please login to continue.",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+250123456789"
    }
  }
}
```

**Note:** Password confirmation should be handled on the frontend.

---

### 2. Login (Step 1) - Get OTP
```http
POST /auth/v1/login/
```

**Request:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to your email. Please verify to complete login.",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "expires_in": 300
  }
}
```

**Note:** Check your email or terminal for the 6-digit OTP code.

---

### 3. Verify OTP (Step 2) - Get Tokens
```http
POST /auth/v1/login/verify-otp/
```

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "user",
      "is_vendor_role": false,
      "phone_number": "+250123456789",
      "last_login": "2025-11-10T14:30:00Z"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
  }
}
```

**💡 Save these tokens!** You'll need them for all subsequent requests.

---

### 4. Refresh Access Token
```http
POST /auth/v1/token/refresh/
```

**Request:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access": "new_access_token_here"
  }
}
```

---

### 5. Logout
```http
POST /auth/v1/logout/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

## 🏪 Product/Dashboard Endpoints

### 6. Get Dashboard (Browse Products)
```http
GET /auth/v1/dashboard/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)
- `search` - Search in title/description
- `category` - Filter by category
- `sort` - Sort by: `price_asc`, `price_desc`, `newest`, `oldest`, `popular`

**Example:**
```
GET /auth/v1/dashboard/?page=1&page_size=20&category=electronics&sort=newest
```

**Response:**
```json
{
  "success": true,
  "message": "Dashboard data retrieved successfully",
  "data": {
    "posts": [
      {
        "id": 1,
        "title": "iPhone 15 Pro",
        "description": "Latest iPhone model",
        "price": "999.99",
        "category": "electronics",
        "inventory": 5,
        "image": "/media/posts/iphone.jpg",
        "user": {
          "id": 2,
          "username": "vendorjohn",
          "is_vendor_role": true
        },
        "total_likes": 45,
        "total_purchases": 12,
        "average_rating": 4.8,
        "review_count": 8,
        "created_at": "2025-11-10T10:00:00Z",
        "is_liked": false,
        "is_bookmarked": false
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "page_size": 20,
      "total_items": 95,
      "has_next": true,
      "has_previous": false
    },
    "filters": {
      "search_query": "",
      "selected_category": "electronics",
      "available_categories": [
        {"value": "electronics", "label": "Electronics"},
        {"value": "books_media", "label": "Books & Media"}
      ],
      "available_sorts": [
        {"value": "newest", "label": "Newest First"},
        {"value": "price_asc", "label": "Price: Low to High"}
      ]
    },
    "user_info": {
      "id": 1,
      "username": "johndoe",
      "is_vendor_role": false,
      "total_bookmarks": 5,
      "total_liked_posts": 12
    }
  }
}
```

---

### 7. Get Product Details
```http
GET /auth/v1/posts/<post_id>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "post": {
      "id": 1,
      "title": "iPhone 15 Pro",
      "description": "Latest iPhone with amazing features",
      "price": "999.99",
      "category": "electronics",
      "inventory": 5,
      "image": "/media/posts/iphone.jpg",
      "auxiliary_images": [
        "/media/product_gallery/iphone_back.jpg",
        "/media/product_gallery/iphone_box.jpg"
      ],
      "user": {
        "id": 2,
        "username": "vendorjohn",
        "is_vendor_role": true
      },
      "total_likes": 45,
      "total_purchases": 12,
      "average_rating": 4.8,
      "review_count": 8,
      "created_at": "2025-11-10T10:00:00Z",
      "is_liked": false,
      "is_bookmarked": false
    },
    "reviews": [
      {
        "id": 1,
        "reviewer": {
          "id": 3,
          "username": "buyer123"
        },
        "rating": 5,
        "comment": "Amazing product! Highly recommended.",
        "created_at": "2025-11-09T15:30:00Z"
      }
    ]
  }
}
```

---

### 8. Get Categories
```http
GET /auth/v1/categories/
```

**No authentication required**

**Response:**
```json
{
  "success": true,
  "data": {
    "categories": [
      {"value": "electronics", "label": "Electronics"},
      {"value": "books_media", "label": "Books & Media"},
      {"value": "home_kitchen", "label": "Home & Kitchen"},
      {"value": "beauty_care", "label": "Beauty & Personal Care"},
      {"value": "software_services", "label": "Software & Services"},
      {"value": "health_fitness", "label": "Health & Fitness"},
      {"value": "other", "label": "Other"}
    ]
  }
}
```

---

## ❤️ Like Endpoints

### 9. Like/Unlike a Post
```http
POST /auth/v1/like/<post_id>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**No request body needed**

**Response (Liked):**
```json
{
  "success": true,
  "message": "Post liked successfully",
  "data": {
    "liked": true,
    "total_likes": 46
  }
}
```

**Response (Unliked):**
```json
{
  "success": true,
  "message": "Post unliked successfully",
  "data": {
    "liked": false,
    "total_likes": 45
  }
}
```

---

## 🔖 Bookmark Endpoints

### 10. Bookmark/Unbookmark a Post
```http
POST /auth/v1/bookmark/<post_id>/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**No request body needed**

**Response (Bookmarked):**
```json
{
  "success": true,
  "message": "Post bookmarked successfully",
  "data": {
    "bookmarked": true
  }
}
```

**Response (Unbookmarked):**
```json
{
  "success": true,
  "message": "Bookmark removed successfully",
  "data": {
    "bookmarked": false
  }
}
```

---

### 11. Get All My Bookmarks
```http
GET /auth/v1/bookmarks/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "bookmarks": [
      {
        "id": 1,
        "post": {
          "id": 5,
          "title": "MacBook Pro M3",
          "description": "Latest MacBook",
          "price": "1999.99",
          "category": "electronics",
          "image": "/media/posts/macbook.jpg",
          "user": {
            "id": 2,
            "username": "vendorjohn"
          },
          "total_likes": 78,
          "average_rating": 4.9
        },
        "created_at": "2025-11-09T12:00:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 1,
      "total_items": 5
    }
  }
}
```

---

## 🛒 Purchase Endpoints

### 12. Purchase a Product
```http
POST /auth/v1/posts/<post_id>/purchase/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "quantity": 1,
  "delivery_method": "pickup",
  "payment_method": "momo",
  "delivery_address": "123 Main Street, Kigali",
  "delivery_latitude": -1.9441,
  "delivery_longitude": 30.0619
}
```

**Fields:**
- `quantity` - Number of items (required)
- `delivery_method` - `"pickup"` or `"delivery"` (required)
- `payment_method` - `"momo"` or `"credit"` (required)
- `delivery_address` - Required if `delivery_method` is `"delivery"`
- `delivery_latitude` - Optional, for delivery location
- `delivery_longitude` - Optional, for delivery location

**Response:**
```json
{
  "success": true,
  "message": "Purchase created successfully",
  "data": {
    "purchase": {
      "id": 15,
      "order_id": "ORD-A7F3D2E1",
      "product": {
        "id": 1,
        "title": "iPhone 15 Pro",
        "price": "999.99"
      },
      "buyer": {
        "id": 1,
        "username": "johndoe"
      },
      "quantity": 1,
      "purchase_price": "999.99",
      "delivery_fee": "5.00",
      "total_amount": "1004.99",
      "status": "awaiting_pickup",
      "delivery_method": "pickup",
      "payment_method": "momo",
      "created_at": "2025-11-10T14:45:00Z",
      "payment_split": {
        "vendor_amount": "799.99",
        "agaseke_amount": "204.00"
      }
    }
  }
}
```

---

### 13. Get My Purchase History
```http
GET /auth/v1/purchases/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)
- `status` - Filter by status: `pending`, `awaiting_pickup`, `awaiting_delivery`, `out_for_delivery`, `completed`, `cancelled`
- `delivery_method` - Filter by: `pickup`, `delivery`

**Response:**
```json
{
  "success": true,
  "data": {
    "purchases": [
      {
        "id": 15,
        "order_id": "ORD-A7F3D2E1",
        "product": {
          "id": 1,
          "title": "iPhone 15 Pro",
          "image": "/media/posts/iphone.jpg",
          "price": "999.99"
        },
        "vendor": {
          "id": 2,
          "username": "vendorjohn"
        },
        "quantity": 1,
        "purchase_price": "999.99",
        "delivery_fee": "5.00",
        "total_amount": "1004.99",
        "status": "awaiting_pickup",
        "delivery_method": "pickup",
        "payment_method": "momo",
        "delivery_address": null,
        "created_at": "2025-11-10T14:45:00Z",
        "updated_at": "2025-11-10T14:45:00Z"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 2,
      "total_items": 35
    },
    "summary": {
      "total_purchases": 35,
      "total_spent": "15234.50",
      "pending": 2,
      "awaiting_pickup": 1,
      "completed": 32
    }
  }
}
```

---

## ⚙️ User Settings Endpoints

### 14. Get My Profile Settings
```http
GET /auth/v1/settings/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+250123456789",
      "role": "user",
      "is_vendor_role": false,
      "profile_picture": "/media/profile_pics/john.jpg",
      "total_purchases": "1234.50",
      "total_sales": "0.00",
      "date_joined": "2025-10-01T10:00:00Z",
      "last_login": "2025-11-10T14:30:00Z"
    }
  }
}
```

---

### 15. Update My Profile
```http
PUT /auth/v1/settings/
PATCH /auth/v1/settings/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Request (Form Data):**
```
first_name: John
last_name: Doe
email: john@example.com
phone_number: +250123456789
profile_picture: [file]
```

**Response:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+250123456789",
      "profile_picture": "/media/profile_pics/john_new.jpg"
    }
  }
}
```

---

### 16. Become a Vendor
```http
POST /auth/v1/become-vendor/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**No request body needed**

**Response:**
```json
{
  "success": true,
  "message": "You are now a vendor! You can start selling products.",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "is_vendor_role": true
    }
  }
}
```

---

## 📝 Quick Reference - All Endpoints

### Authentication (No Auth Required)
```
POST /auth/v1/register/          - Register new account
POST /auth/v1/login/             - Login step 1 (get OTP)
POST /auth/v1/login/verify-otp/  - Login step 2 (verify OTP, get tokens)
POST /auth/v1/token/refresh/     - Refresh access token
GET  /auth/v1/categories/        - Get product categories
```

### Authenticated Endpoints (Requires Bearer Token)
```
POST /auth/v1/logout/                      - Logout

# Browse & View
GET  /auth/v1/dashboard/                   - Browse all products
GET  /auth/v1/posts/<post_id>/             - View product details

# Interactions
POST /auth/v1/like/<post_id>/              - Like/unlike post
POST /auth/v1/bookmark/<post_id>/          - Bookmark/unbookmark post
GET  /auth/v1/bookmarks/                   - Get my bookmarks

# Shopping
POST /auth/v1/posts/<post_id>/purchase/    - Purchase product
GET  /auth/v1/purchases/                   - Get my purchases

# Profile
GET  /auth/v1/settings/                    - Get my profile
PUT  /auth/v1/settings/                    - Update my profile
POST /auth/v1/become-vendor/               - Upgrade to vendor
```

---

## 🔑 Authentication Header

For all authenticated endpoints, include this header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## ⚠️ Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Authentication required",
  "errors": {
    "auth": ["Please provide valid authentication credentials"]
  }
}
```

### 404 Not Found
```json
{
  "success": false,
  "message": "Resource not found",
  "errors": {
    "resource": ["The requested resource was not found"]
  }
}
```

### 500 Server Error
```json
{
  "success": false,
  "message": "Internal server error",
  "errors": {
    "server": ["An unexpected error occurred"]
  }
}
```

---

## 🧪 Testing Examples

### cURL Examples

**1. Register:**
```bash
curl -X POST http://localhost:8000/auth/v1/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password1": "SecurePass123",
    "password2": "SecurePass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

**2. Login:**
```bash
curl -X POST http://localhost:8000/auth/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123"
  }'
```

**3. Verify OTP:**
```bash
curl -X POST http://localhost:8000/auth/v1/login/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "otp_code": "123456"
  }'
```

**4. Browse Products:**
```bash
curl -X GET "http://localhost:8000/auth/v1/dashboard/?page=1&category=electronics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**5. Like a Post:**
```bash
curl -X POST http://localhost:8000/auth/v1/like/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**6. Purchase a Product:**
```bash
curl -X POST http://localhost:8000/auth/v1/posts/1/purchase/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 1,
    "delivery_method": "pickup",
    "payment_method": "momo"
  }'
```

---

## 💡 Tips & Best Practices

1. **Store Tokens Securely**
   - Save access and refresh tokens in secure storage
   - Don't store in localStorage for sensitive apps

2. **Handle Token Expiry**
   - Access tokens expire after 60 minutes
   - Use refresh token to get new access token
   - If refresh fails, user must login again

3. **Check OTP Email**
   - In development, check terminal for OTP
   - In production, check email inbox/spam

4. **Pagination**
   - Use `page` and `page_size` params for large lists
   - Default page_size is 20, max is 100

5. **Error Handling**
   - Always check `success` field in response
   - Display `message` to users
   - Use `errors` object for field-specific errors

---

## 📞 Support

- **Documentation:** See `API_AUTHENTICATION_FLOW.md` for detailed auth flow
- **Changelog:** See `CHANGELOG_OTP_LOGIN.md` for recent changes
- **Email Setup:** See `EMAIL_CONFIGURATION_GUIDE.md` for email config

---

**Happy Coding! 🚀**

