# API Authentication Flow & Response Guide

## ✅ What We Have

### 1. **Access & Refresh Tokens** ✅ YES!

After **login** or **signup**, you receive **JWT tokens**:

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
      "last_login": "2025-01-15T10:30:00Z"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",  // ← Use this for API calls
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."  // ← Use this to get new access token
    }
  }
}
```

**Token Lifetimes:**
- **Access Token**: 60 minutes (1 hour)
- **Refresh Token**: 7 days

---

## 🔐 Authentication Endpoints

### POST `/auth/v1/register/`
**Sign Up** - Creates new account

**Request:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password1": "securepassword123",
  "password2": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:** ✅ Returns user + **access & refresh tokens**
```json
{
  "success": true,
  "message": "Account created successfully",
  "data": {
    "user": { ... },
    "tokens": {
      "access": "...",
      "refresh": "..."
    }
  }
}
```

---

### POST `/auth/v1/login/`
**Login** - Authenticate existing user

**Request:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:** ✅ Returns user + **access & refresh tokens**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { ... },
    "tokens": {
      "access": "...",
      "refresh": "..."
    }
  }
}
```

---

### POST `/auth/v1/token/refresh/`
**Refresh Access Token** - Get new access token when it expires

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

## 🛍️ Using Tokens in API Requests

After login/signup, **store the tokens** and use the **access token** in all API requests:

```bash
# Example API call with JWT token
curl -X GET http://localhost:8000/auth/v1/dashboard/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

**Header Format:**
```
Authorization: Bearer <access_token>
```

---

## 📋 What Happens After Login/Signup?

### Step-by-Step Flow:

1. **User registers/logs in** → Receives:
   - ✅ User profile data
   - ✅ **Access token** (valid 60 minutes)
   - ✅ **Refresh token** (valid 7 days)

2. **Store tokens securely** (client-side):
   ```javascript
   // Example: Store in localStorage or secure storage
   localStorage.setItem('access_token', response.data.tokens.access);
   localStorage.setItem('refresh_token', response.data.tokens.refresh);
   ```

3. **Use access token for all API calls:**
   ```javascript
   // Example: Get dashboard/products
   fetch('/auth/v1/dashboard/', {
     headers: {
       'Authorization': `Bearer ${accessToken}`
     }
   })
   ```

4. **When access token expires** (after 60 minutes):
   - API returns `401 Unauthorized`
   - Use refresh token to get new access token:
   ```javascript
   fetch('/auth/v1/token/refresh/', {
     method: 'POST',
     body: JSON.stringify({ refresh: refreshToken })
   })
   ```

5. **Refresh token expires** (after 7 days):
   - User must login again to get new tokens

---

## 🏪 Vendor Application

### Current Status: ❌ **Missing API Endpoint**

There's a **HTML view** for becoming a vendor (`/auth/become-vendor/`), but **NO JSON API endpoint yet**.

**What we need:**
- `POST /auth/v1/become-vendor/` - API endpoint to upgrade user to vendor

**Current HTML view:**
- `POST /auth/become-vendor/` - Sets `is_vendor_role = True`

---

## 📊 Complete Authentication Flow

```
┌─────────────────┐
│  1. Register    │ → POST /auth/v1/register/
│   OR Login      │ → POST /auth/v1/login/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Get Tokens   │ → { access: "...", refresh: "..." }
│    + User Data   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Store Tokens │ → localStorage / SecureStorage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. API Calls    │ → Authorization: Bearer <access_token>
│  - Dashboard    │ → GET /auth/v1/dashboard/
│  - Products     │ → GET /auth/v1/posts/<id>/
│  - Purchase     │ → POST /auth/v1/posts/<id>/purchase/
└────────┬────────┘
         │
         ▼ (after 60 min)
┌─────────────────┐
│ 5. Refresh      │ → POST /auth/v1/token/refresh/
│    Access Token │ → { refresh: "..." }
└─────────────────┘
```

---

## 🎯 Summary

### ✅ What You Get After Login/Signup:
1. **User Profile** (id, username, email, role, is_vendor_role, etc.)
2. **Access Token** (60 min lifetime) - Use for API calls
3. **Refresh Token** (7 days lifetime) - Use to refresh access token

### ❌ What's Missing:
- **Vendor Application API** - Need to create `POST /auth/v1/become-vendor/`

---

## 🔧 Next Steps

1. ✅ **Tokens are working** - Access & refresh tokens are implemented
2. ❌ **Add Vendor API** - Create JSON API endpoint for vendor upgrade
3. ✅ **All other endpoints ready** - Use JWT tokens for authentication

