# Registration API - Quick Reference

## 🚀 Single Password Registration

### Endpoint
```
POST /auth/v1/register/
```

### Request
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

### Response (Success)
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

---

## ✅ Validation Rules

| Field | Rule |
|-------|------|
| username | Min 3 chars, unique |
| email | Valid format, unique |
| password | Min 8 chars |
| first_name | Required |
| last_name | Required |
| phone_number | Min 10 digits |

---

## ⚠️ Important Notes

1. **Single Password Field**: Only `password` required (not `password1` and `password2`)
2. **No Tokens**: User must login after registration to get tokens
3. **Frontend Validation**: Password confirmation handled on frontend
4. **Breaking Change**: Old two-password format no longer works

---

## 📝 Example (cURL)

```bash
curl -X POST http://localhost:8000/auth/v1/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "mypassword123",
    "first_name": "New",
    "last_name": "User",
    "phone_number": "1234567890"
  }'
```

---

## 🔴 Common Errors

```json
// Short password
{
  "success": false,
  "errors": {
    "password": ["Password must be at least 8 characters long"]
  }
}

// Duplicate username
{
  "success": false,
  "errors": {
    "username": ["A user with that username already exists"]
  }
}

// Invalid email
{
  "success": false,
  "errors": {
    "email": ["Enter a valid email address"]
  }
}
```

---

For complete details, see **`CHANGELOG_SINGLE_PASSWORD_REGISTRATION.md`**

