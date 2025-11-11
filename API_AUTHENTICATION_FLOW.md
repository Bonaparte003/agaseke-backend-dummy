# API Authentication Flow & Response Guide

## ✅ What We Have

### 1. **OTP-Protected Login** 🔐 YES!

Login now requires **2-Factor Authentication** with OTP:
- Step 1: Submit credentials → Get session_id + OTP sent to email
- Step 2: Submit OTP code → Get JWT tokens

### 2. **Access & Refresh Tokens** ✅ YES!

After **OTP verification**, you receive **JWT tokens**:

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

**Response:** ✅ Returns user data only (no tokens)
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
      "role": "user",
      "is_vendor_role": false,
      "phone_number": "+250123456789"
    }
  }
}
```

**Note:** Users must explicitly login after registration to receive tokens.

---

### POST `/auth/v1/login/`
**Login Step 1** - Authenticate existing user and send OTP

**Request:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:** ✅ Returns session_id and sends OTP to email
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

**Note:** An OTP code will be sent to the user's email. This code is valid for 5 minutes.

---

### POST `/auth/v1/login/verify-otp/`
**Login Step 2** - Verify OTP and get tokens

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "otp_code": "123456"
}
```

**Response:** ✅ Returns user + **access & refresh tokens**
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
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
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

After **OTP verification**, **store the tokens** and use the **access token** in all API requests:

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

## 📧 OTP Email

When you login, you'll receive an email with:
- 6-digit OTP code
- Valid for **5 minutes**
- Beautiful HTML email template
- Plain text fallback for compatibility

---

## 📋 What Happens After Registration & Login?

### Step-by-Step Flow:

1. **User registers** → Receives:
   - ✅ User profile data
   - ❌ **No tokens** (must login separately)

2. **User logs in (Step 1)** → Receives:
   - ✅ **Session ID**
   - ✅ **OTP sent to email** (valid 5 minutes)

3. **User verifies OTP (Step 2)** → Receives:
   - ✅ User profile data
   - ✅ **Access token** (valid 60 minutes)
   - ✅ **Refresh token** (valid 7 days)

4. **Store tokens securely** (client-side):
   ```javascript
   // Example: Store in localStorage or secure storage
   localStorage.setItem('access_token', response.data.tokens.access);
   localStorage.setItem('refresh_token', response.data.tokens.refresh);
   ```

5. **Use access token for all API calls:**
   ```javascript
   // Example: Get dashboard/products
   fetch('/auth/v1/dashboard/', {
     headers: {
       'Authorization': `Bearer ${accessToken}`
     }
   })
   ```

6. **When access token expires** (after 60 minutes):
   - API returns `401 Unauthorized`
   - Use refresh token to get new access token:
   ```javascript
   fetch('/auth/v1/token/refresh/', {
     method: 'POST',
     body: JSON.stringify({ refresh: refreshToken })
   })
   ```

7. **Refresh token expires** (after 7 days):
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
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Get User     │ → Returns user data only (NO TOKENS)
│    Data Only    │ → Must login to get tokens
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Login       │ → POST /auth/v1/login/
│    (Step 1)     │ → Send username + password
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. Get Session  │ → Returns session_id
│    + OTP Email  │ → OTP sent to user's email (5 min expiry)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Verify OTP   │ → POST /auth/v1/login/verify-otp/
│    (Step 2)     │ → Send session_id + otp_code
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. Get Tokens   │ → { access: "...", refresh: "..." }
│    + User Data  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. Store Tokens │ → localStorage / SecureStorage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 8. API Calls    │ → Authorization: Bearer <access_token>
│  - Dashboard    │ → GET /auth/v1/dashboard/
│  - Products     │ → GET /auth/v1/posts/<id>/
│  - Purchase     │ → POST /auth/v1/posts/<id>/purchase/
└────────┬────────┘
         │
         ▼ (after 60 min)
┌─────────────────┐
│ 9. Refresh      │ → POST /auth/v1/token/refresh/
│    Access Token │ → { refresh: "..." }
└─────────────────┘
```

---

## 🎯 Summary

### ✅ What You Get After Registration:
1. **User Profile** (id, username, email, role, is_vendor_role, etc.)
2. ❌ **No Tokens** - Must login separately

### ✅ What You Get After Login Step 1:
1. **Session ID** - For OTP verification
2. **OTP Email** - 6-digit code sent to your email (valid 5 minutes)

### ✅ What You Get After Login Step 2 (OTP Verification):
1. **User Profile** (id, username, email, role, is_vendor_role, etc.)
2. **Access Token** (60 min lifetime) - Use for API calls
3. **Refresh Token** (7 days lifetime) - Use to refresh access token

---

## 🔧 Implementation Highlights

1. ✅ **2-Factor Authentication (2FA)** - Login protected with OTP verification
2. ✅ **Email OTP Delivery** - Beautiful HTML emails with 6-digit codes
3. ✅ **Session Management** - Secure session IDs for OTP validation
4. ✅ **Registration separated from login** - Users must explicitly login after registration
5. ✅ **JWT Tokens** - Access & refresh tokens are implemented
6. ✅ **Vendor API added** - JSON API endpoint for vendor upgrade exists
7. ✅ **Time-based expiry** - OTPs expire after 5 minutes, tokens have defined lifetimes

