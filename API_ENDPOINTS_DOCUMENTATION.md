# agaseke API Endpoints Documentation

## 📋 Table of Contents
1. [URL Structure Overview](#url-structure-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Web Endpoints (HTML Responses)](#web-endpoints-html-responses)
4. [API Endpoints (JSON Responses)](#api-endpoints-json-responses)
5. [API Flow Diagrams](#api-flow-diagrams)
6. [Return Types Reference](#return-types-reference)

---

## URL Structure Overview

```
Base URL: http://127.0.0.1:8000/

├── /                          → Redirects to /auth/login/
├── /admin/                    → Django Admin Panel
└── /auth/                     → Main Application URLs
    ├── /auth/register/        → User Registration (Web)
    ├── /auth/login/           → User Login (Web)
    ├── /auth/logout/          → User Logout (Web)
    ├── /auth/dashboard/       → Product Dashboard (Web)
    ├── /auth/settings/        → User Settings (Web)
    │
    ├── /auth/v1/              → Legacy JSON API (v1)
    │   ├── /v1/register/      → Registration API
    │   ├── /v1/login/         → Login API
    │   ├── /v1/logout/        → Logout API
    │   ├── /v1/dashboard/     → Dashboard Data API
    │   ├── /v1/bookmark/<id>/ → Bookmark Toggle API
    │   ├── /v1/like/<id>/     → Like Toggle API
    │   └── /v1/categories/    → Categories List API
    │
    └── /auth/api/             → Functional API Endpoints
        ├── /api/purchases/by-qr/        → Get Purchases from QR
        ├── /api/verify-credentials/     → Verify Buyer Credentials
        ├── /api/send-otp/               → Send OTP Email
        ├── /api/verify-otp/             → Verify OTP Code
        ├── /api/complete-purchase/      → Complete Purchase Pickup
        └── /api/vendor-statistics/<id>/ → Vendor Statistics Modal
```

---

## Authentication & Authorization

### Authentication Methods

1. **Session-Based** (Web)
   - Uses Django session cookies
   - Automatic login after registration
   - Used for: `/auth/*` web endpoints

2. **Token-Based** (v1 API)
   - Bearer token in `Authorization` header
   - Used for: `/auth/v1/*` endpoints
   - Token obtained via `/auth/v1/login/`

### User Roles

- **user** - Regular buyer
- **vendor** - Can create products (`is_vendor_role=True`)
- **staff** - Admin access
- **agaseke** - Platform operator (handles pickups/deliveries)

---

## Web Endpoints (HTML Responses)

These endpoints return HTML pages for web browser access.

| Endpoint | Method | Auth | App | Returns |
|----------|--------|------|-----|---------|
| `/auth/register/` | GET, POST | None | authentication | HTML: Registration form |
| `/auth/login/` | GET, POST | None | authentication | HTML: Login form |
| `/auth/logout/` | GET | Session | authentication | Redirect to login |
| `/auth/dashboard/` | GET | Session | authentication | HTML: Product listing page |
| `/auth/settings/` | GET, POST | Session | users | HTML: User settings page |
| `/auth/post/<id>/` | GET | Session | posts | HTML: Product detail page |
| `/auth/create-product/` | GET, POST | Session | products | HTML: Product creation form |
| `/auth/edit-product/<id>/` | GET, POST | Session | products | HTML: Product edit form |
| `/auth/purchases/` | GET | Session | users | HTML: Purchase history page |
| `/auth/bookmarks/` | GET | Session | posts | HTML: Bookmarks page |
| `/auth/vendor-dashboard/` | GET | Session (vendor) | users | HTML: Vendor dashboard |
| `/auth/agaseke-dashboard/` | GET | Session (agaseke) | authentication | HTML: agaseke dashboard |
| `/auth/scan-qr/` | GET, POST | Session (agaseke) | authentication | HTML: QR scanner page |

---

## API Endpoints (JSON Responses)

---

### 🔑 Legacy v1 API Endpoints

**Base URL:** `/auth/v1/`

| Endpoint | Method | Auth | Description | Returns |
|----------|--------|------|-------------|---------|
| `/v1/register/` | POST | None | User registration | JSON: User + success |
| `/v1/login/` | POST | None | User login | JSON: User + token |
| `/v1/logout/` | POST | Token | User logout | JSON: Message |
| `/v1/dashboard/` | GET | Token | Dashboard data | JSON: Posts + filters |
| `/v1/bookmark/<id>/` | POST | Token | Toggle bookmark | JSON: Bookmark status |
| `/v1/like/<id>/` | POST | Token | Toggle like | JSON: Like status |
| `/v1/categories/` | GET | None | Get categories | JSON: Categories list |

**v1 Dashboard Response (200 OK):**
```json
{
  "success": true,
  "message": "Dashboard data retrieved successfully",
  "data": {
    "posts": [...],
    "pagination": {
      "current_page": 1,
      "total_pages": 5,
      "page_size": 20,
      "total_items": 100,
      "has_next": true,
      "has_previous": false
    },
    "filters": {
      "search_query": "",
      "selected_category": "",
      "available_categories": [...],
      "available_sorts": [...]
    },
    "user_info": {
      "id": 1,
      "username": "john_doe",
      "is_vendor_role": false,
      "total_bookmarks": 8,
      "total_liked_posts": 15
    }
  }
}
```

---

### 🔐 Functional API Endpoints (QR Flow)

**Base URL:** `/auth/api/`

| Endpoint | Method | Auth | Description | Returns |
|----------|--------|------|-------------|---------|
| `/api/purchases/by-qr/` | POST | Session (agaseke) | Get purchases from QR | JSON: Purchases + buyer |
| `/api/verify-credentials/` | POST | Session (agaseke) | Verify buyer credentials | JSON: Verification result |
| `/api/send-otp/` | POST | Session (agaseke) | Send OTP email | JSON: Success message |
| `/api/verify-otp/` | POST | Session (agaseke) | Verify OTP code | JSON: Verification result |
| `/api/complete-purchase/` | POST | Session (agaseke) | Complete purchase | JSON: Purchase result |
| `/api/vendor-statistics/<id>/` | GET | Session (agaseke) | Vendor stats modal | JSON: Statistics |

**Verify Credentials Response (200 OK):**
```json
{
  "success": true,
  "message": "Credentials verified successfully",
  "user_id": 1,
  "username": "john_doe"
}
```

**Send OTP Response (200 OK):**
```json
{
  "success": true,
  "message": "OTP sent successfully to user email",
  "otp_id": 123
}
```

**Verify OTP Response (200 OK):**
```json
{
  "success": true,
  "message": "OTP verified successfully",
  "verified": true
}
```

---

## API Flow Diagrams

### 1. User Registration & Login Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ POST /auth/v1/register/
       ├─────────────────────────────────────┐
       │ { username, email, password, ... }  │
       └─────────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Registration API   │
│  (v1 API)            │
└──────────┬──────────┘
           │
           │ Creates User + Auto-login
           │
           ▼
┌─────────────────────┐
│  Response (200)     │
│  - User data        │
│  - Auth token       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Client stores      │
│  - Auth token       │
└─────────────────────┘
```

### 2. Product Purchase Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       │ GET /auth/v1/dashboard/
       ├─────────────────────────┐
       │ Browse products          │
       └─────────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Select Product     │
│  (Web page)          │
└──────────┬──────────┘
           │
           │ POST /auth/post/<id>/purchase/
           ├─────────────────────────────┐
           │ { quantity, delivery_method }│
           └─────────────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Purchase Created   │
│  Status: awaiting   │
│  Inventory updated  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  QR Code Updated    │
│  (for pickup)       │
└─────────────────────┘
```

### 3. QR Code Pickup Flow (agaseke)

```
┌─────────────┐     ┌─────────────┐
│   Buyer     │     │   agaseke   │
└──────┬──────┘     └──────┬──────┘
       │                    │
       │ Shows QR Code      │
       ├───────────────────►
       │                    │
       │                    │ POST /auth/api/purchases/by-qr/
       │                    ├─────────────────────┐
       │                    │ { qr_data }         │
       │                    └─────────────────────┘
       │                    │
       │                    ▼
       │            ┌─────────────────────┐
       │            │ Decode QR → Get      │
       │            │ Purchases            │
       │            └──────────┬───────────┘
       │                    │
       │                    │ Returns: Purchases list
       │                    │
       │◄───────────────────┤
       │                    │
       │                    │ POST /api/verify-credentials/
       │                    ├─────────────────────┐
       │                    │ { username,         │
       │                    │   password, user_id }│
       │                    └─────────────────────┘
       │                    │
       │                    ▼
       │            ┌─────────────────────┐
       │            │ Verify Buyer        │
       │            │ Credentials         │
       │            └──────────┬───────────┘
       │                    │
       │                    │ POST /api/send-otp/
       │                    │
       │                    ▼
       │            ┌─────────────────────┐
       │            │ OTP Sent to Email   │
       │            └──────────┬───────────┘
       │                    │
       │                    │ Buyer enters OTP
       │                    │
       │                    │ POST /api/verify-otp/
       │                    ├─────────────────────┐
       │                    │ { user_id, otp }    │
       │                    └─────────────────────┘
       │                    │
       │                    ▼
       │            ┌─────────────────────┐
       │            │ OTP Verified         │
       │            └──────────┬───────────┘
       │                    │
       │                    │ POST /auth/api/complete-purchase/
       │                    ├─────────────────────┐
       │                    │ { purchase_id }    │
       │                    └─────────────────────┘
       │                    │
       │                    ▼
       │            ┌─────────────────────┐
       │            │ Purchase Completed   │
       │            │ - Status: completed  │
       │            │ - Payment split:     │
       │            │   80% vendor         │
       │            │   20% agaseke        │
       │            └─────────────────────┘
```

---

## Return Types Reference

### Standard Response Formats

#### ✅ Success Response (200 OK)
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

#### ✅ Created Response (201 Created)
```json
{
  "message": "Resource created successfully",
  "id": 1,
  "data": { ... }
}
```

#### ❌ Error Response (400 Bad Request)
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

#### ❌ Unauthorized (401 Unauthorized)
```json
{
  "success": false,
  "message": "Authentication required",
  "errors": {
    "auth": ["Please provide valid authentication credentials"]
  }
}
```

#### ❌ Forbidden (403 Forbidden)
```json
{
  "error": "Permission denied",
  "detail": "You do not have permission to perform this action"
}
```

#### ❌ Not Found (404 Not Found)
```json
{
  "error": "Resource not found",
  "detail": "No resource matches the given query"
}
```

#### ❌ Server Error (500 Internal Server Error)
```json
{
  "success": false,
  "message": "Internal server error",
  "errors": {
    "server": ["An unexpected error occurred"]
  }
}
```

### Pagination Response Format

```json
{
  "count": 100,
  "next": "http://127.0.0.1:8000/auth/api/rest/posts/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Filtering & Query Parameters

**Common Query Parameters:**
- `?page=1` - Page number
- `?page_size=20` - Items per page (max 100)
- `?search=query` - Search term
- `?ordering=-created_at` - Sort order
- `?category=electronics` - Filter by category
- `?status=completed` - Filter by status

---

## Authentication Headers

### Session Authentication (Web)
```
Cookie: sessionid=abc123...
```

### Token Authentication (v1 API)
```
Authorization: Bearer <token_key>
```

---

## Status Codes Reference

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation errors |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Internal server error |

---

## Common Workflows

### Workflow 1: New User Registration & First Purchase

```
1. POST /auth/v1/register/
   → Returns: User + Auth token

2. GET /auth/v1/dashboard/
   → Returns: Product list

3. GET /auth/post/<id>/
   → Returns: Product details (Web page)

4. POST /auth/post/<id>/purchase/
   → Returns: Purchase created
   → Status: awaiting_pickup

5. GET /auth/purchases/
   → Returns: User's purchase history (Web page)
```

### Workflow 2: Vendor Creates & Manages Products

```
1. POST /auth/v1/register/
   → Register as user

2. POST /auth/become-vendor/
   → Convert to vendor (Web)

3. GET /auth/create-product/
   → Create product listing (Web form)

4. GET /auth/vendor-dashboard/
   → View sales dashboard (Web)

5. GET /auth/agaseke-history/
   → View purchase history (if agaseke)
```

### Workflow 3: agaseke QR Code Pickup Process

```
1. POST /auth/api/purchases/by-qr/
   → Scan QR → Get purchases

2. POST /auth/api/verify-credentials/
   → Verify buyer identity

3. POST /auth/api/send-otp/
   → Send OTP to buyer email

4. POST /auth/api/verify-otp/
   → Verify OTP code

5. POST /auth/api/complete-purchase/
   → Complete purchase
   → Calculate payment splits
```

---

## Endpoint Summary by App

| App | Endpoints | Purpose |
|-----|-----------|---------|
| **users** | `/auth/settings/`, `/auth/vendor-dashboard/` | User management & vendor features |
| **posts** | `/auth/post/<id>/`, `/auth/bookmark/<id>/`, `/auth/like-post/<id>/` | Products/Posts & interactions |
| **products** | `/auth/post/<id>/purchase/`, `/auth/purchases/` | Purchase management |
| **authentication** | `/auth/qr-code/`, `/auth/api/purchases/by-qr/`, `/auth/api/verify-otp/` | Auth & QR flow |

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Currency values are Decimal strings (e.g., "100.00")
- Image URLs are relative paths from MEDIA_URL
- Auth tokens (v1 API) do not expire (but can be regenerated on logout/login)
- Pagination default: 20 items per page, max 100
- All POST requests require `Content-Type: application/json` or `multipart/form-data` for file uploads

---

**Last Updated:** November 4, 2025
**API Version:** 1.0 (v1 API)

