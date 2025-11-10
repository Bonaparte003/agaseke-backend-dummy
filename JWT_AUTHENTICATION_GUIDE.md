# JWT Authentication Guide

## ✅ Implementation Complete!

JWT (JSON Web Token) authentication with access and refresh tokens has been successfully implemented for mobile app support.

## 🔑 Token Endpoints

### Base URL
```
http://localhost:8000/auth/api/rest/
```

### 1. Obtain Access & Refresh Tokens
**Endpoint:** `POST /auth/api/rest/auth/token/`

**Description:** Get access and refresh tokens by providing username and password.

**Request:**
```json
{
    "username": "johndoe",
    "password": "securepassword"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "user",
        "is_vendor_role": false
    },
    "message": "Login successful"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/api/rest/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securepassword"
  }'
```

### 2. Refresh Access Token
**Endpoint:** `POST /auth/api/rest/auth/token/refresh/`

**Description:** Get a new access token using your refresh token.

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/api/rest/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "your_refresh_token_here"
  }'
```

### 3. Verify Token
**Endpoint:** `POST /auth/api/rest/auth/token/verify/`

**Description:** Verify if an access token is valid.

**Request:**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (Valid):**
```json
{}
```

**Response (Invalid):**
```json
{
    "detail": "Token is invalid or expired"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/api/rest/auth/token/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_access_token_here"
  }'
```

## 📱 Using Tokens in API Requests

### Authentication Header Format
Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Example API Request
```bash
curl -X GET http://localhost:8000/auth/api/rest/posts/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json"
```

## 🔐 Token Configuration

### Token Lifetimes
- **Access Token:** 60 minutes (1 hour)
- **Refresh Token:** 7 days

### Security Features
- ✅ **Token Rotation:** New refresh token generated on each refresh
- ✅ **Blacklisting:** Old refresh tokens are blacklisted after rotation
- ✅ **Last Login Update:** User's last_login field is updated on token generation
- ✅ **Bearer Token Format:** Uses standard Bearer token authentication

## 📋 Registration with Tokens

When a user registers, JWT tokens are automatically generated:

**Endpoint:** `POST /auth/api/rest/auth/register/`

**Response:**
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "newuser",
        "email": "newuser@example.com",
        ...
    },
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
}
```

## 🔄 Mobile App Authentication Flow

### Initial Login
1. User enters username/password
2. App calls `POST /auth/api/rest/auth/token/`
3. App receives `access` and `refresh` tokens
4. App stores tokens securely (e.g., Keychain/SecureStorage)
5. App includes `Authorization: Bearer <access_token>` in all API requests

### Token Refresh (When Access Token Expires)
1. App detects 401 Unauthorized response
2. App calls `POST /auth/api/rest/auth/token/refresh/` with refresh token
3. App receives new access token
4. App retries original request with new access token
5. If refresh fails, redirect to login screen

### Logout
1. App can call `POST /auth/api/rest/auth/logout/` (session-based)
2. Or simply delete tokens from local storage
3. If using blacklist (optional), tokens can be explicitly invalidated

## 🛠️ Implementation Details

### Settings Configuration
Located in `agaseke/settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    ...
}
```

### REST Framework Configuration
JWT authentication is added as the primary authentication method:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Primary
        'rest_framework.authentication.SessionAuthentication',        # Web support
        'rest_framework.authentication.BasicAuthentication',         # Fallback
    ],
    ...
}
```

## 🔒 Security Best Practices

### For Mobile Apps
1. **Secure Storage:** Store tokens in secure storage (iOS Keychain, Android Keystore)
2. **Token Refresh:** Implement automatic token refresh before expiration
3. **Error Handling:** Handle 401 errors gracefully and refresh tokens
4. **Logout:** Clear tokens from storage on logout
5. **HTTPS Only:** Always use HTTPS in production

### For Backend
1. **Token Expiration:** Access tokens expire in 1 hour (short-lived)
2. **Refresh Rotation:** New refresh tokens generated on each refresh
3. **Blacklisting:** Old refresh tokens are automatically blacklisted
4. **Secret Key:** Ensure `SECRET_KEY` is kept secure

## 📝 Testing

### Test Token Obtainment
```bash
# Register user
curl -X POST http://localhost:8000/auth/api/rest/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123"
  }'

# Get tokens
curl -X POST http://localhost:8000/auth/api/rest/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### Test Protected Endpoint
```bash
# Use access token to access protected endpoint
curl -X GET http://localhost:8000/auth/api/rest/posts/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## 🐛 Troubleshooting

### Token Expired
**Error:** `{"detail": "Token is invalid or expired"}`

**Solution:** Use refresh token to get new access token

### Invalid Credentials
**Error:** `{"detail": "No active account found with the given credentials"}`

**Solution:** Verify username/password are correct

### Token Not Sent
**Error:** `{"detail": "Authentication credentials were not provided."}`

**Solution:** Include `Authorization: Bearer <token>` header in request

## ✅ What's Working

- ✅ Access token generation (1 hour lifetime)
- ✅ Refresh token generation (7 days lifetime)
- ✅ Token refresh endpoint
- ✅ Token verification endpoint
- ✅ Automatic token rotation
- ✅ Blacklist support (if configured)
- ✅ User data included in token response
- ✅ Compatible with existing session-based auth (web)

## 🚀 Next Steps (Optional)

1. **Enable Token Blacklist** (recommended for production):
   - Install: `pip install djangorestframework-simplejwt[token_blacklist]`
   - Add to `INSTALLED_APPS`: `'rest_framework_simplejwt.token_blacklist'`
   - Run migrations: `python manage.py migrate`

2. **Custom Token Claims** (optional):
   - Add custom data to JWT payload (user role, permissions, etc.)

3. **Rate Limiting** (recommended):
   - Add rate limiting to token endpoints to prevent brute force attacks

## 📚 Additional Resources

- [djangorestframework-simplejwt Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io](https://jwt.io/) - JWT debugger and information

