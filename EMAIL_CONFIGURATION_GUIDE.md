# Email Configuration Guide

## Current Setup ✅

Your project is now configured to **automatically use the correct email backend** based on the environment:

- **Development** (`DEBUG=True`): Prints emails to console/terminal
- **Production** (`DEBUG=False`): Sends real emails via SMTP

---

## Development Mode (Current)

Since you're in development mode, OTP emails will be **printed to your terminal** instead of being sent.

### How It Works:

1. When a user logs in, an OTP is generated
2. Instead of sending an email, the OTP will appear in your terminal/console
3. You can copy the OTP code and use it for testing

### Example Terminal Output:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: =?utf-8?b?8J+UkCBhZ2FzZWtlIC0gWW91ciBWZXJpZmljYXRpb24gQ29kZQ==?=
From: KoraQuest <noreply@koraquest.com>
To: user@example.com
Date: Sun, 10 Nov 2025 14:42:18 -0000
Message-ID: <...>

agaseke - Login Verification Required

Hello John!

Please verify your identity to complete your login. Your verification code is:

123456

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Best regards,
agaseke Team
```

### Testing Your Login:

1. Make a login request to `/auth/v1/login/`
2. Check your terminal for the OTP code (look for a 6-digit number)
3. Use that code with `/auth/v1/login/verify-otp/`

---

## Production Mode Setup

When you deploy to production (`DEBUG=False`), you'll need to configure real email sending.

### Option 1: Gmail (Recommended for Testing)

#### Step 1: Enable 2-Factor Authentication
1. Go to [Google Account Settings](https://myaccount.google.com/security)
2. Enable **2-Step Verification**

#### Step 2: Generate App Password
1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Other (Custom name)"
3. Enter "KoraQuest" as the name
4. Click **Generate**
5. Copy the 16-character password

#### Step 3: Update Settings
In `agaseke/settings.py`, update the production email settings:

```python
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-16-char-app-password'  # NOT your regular password
```

### Option 2: Professional Email Service (Recommended for Production)

For production, consider using a dedicated email service:

#### SendGrid
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = 'your-sendgrid-api-key'
```

#### Amazon SES
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-ses-username'
EMAIL_HOST_PASSWORD = 'your-ses-password'
```

#### Mailgun
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'postmaster@your-domain.mailgun.org'
EMAIL_HOST_PASSWORD = 'your-mailgun-password'
```

---

## Testing OTP Login Flow

### Step 1: Start Server
```bash
python manage.py runserver
```

### Step 2: Make Login Request
```bash
curl -X POST http://localhost:8000/auth/v1/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword"
  }'
```

### Step 3: Check Terminal for OTP
Look in your terminal where the server is running. You'll see the email content with the OTP code.

### Step 4: Verify OTP
```bash
curl -X POST http://localhost:8000/auth/v1/login/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-id-from-step-2",
    "otp_code": "123456"
  }'
```

---

## Troubleshooting

### Problem: "No emails showing in terminal"

**Solution:** Make sure you're watching the terminal where `python manage.py runserver` is running.

### Problem: "Still getting SMTP errors"

**Solution:** 
1. Restart your development server: `Ctrl+C` then `python manage.py runserver`
2. Verify `DEBUG = True` in your settings
3. Check that you saved the settings file

### Problem: "Invalid credentials in production"

**Solution:**
1. Verify you're using an **App Password**, not your regular Gmail password
2. Make sure 2-Factor Authentication is enabled
3. Try generating a new App Password

### Problem: "Emails not being delivered"

**Solution:**
1. Check spam folder
2. Verify `DEFAULT_FROM_EMAIL` is set correctly
3. For Gmail: Make sure "Less secure app access" is NOT enabled (use App Passwords instead)
4. Check email service logs/dashboard

---

## Environment Variables (Recommended for Production)

Instead of hardcoding credentials in settings.py, use environment variables:

### Update settings.py:
```python
import os

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
```

### Set environment variables:
```bash
# Linux/Mac
export EMAIL_HOST_USER="your-email@gmail.com"
export EMAIL_HOST_PASSWORD="your-app-password"

# Windows
set EMAIL_HOST_USER=your-email@gmail.com
set EMAIL_HOST_PASSWORD=your-app-password
```

### Or use a .env file with python-decouple:
```bash
pip install python-decouple
```

Create `.env` file:
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

Update settings.py:
```python
from decouple import config

EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

---

## Email Delivery Best Practices

### 1. SPF Records
Add SPF record to your domain's DNS:
```
v=spf1 include:_spf.google.com ~all
```

### 2. DKIM
Configure DKIM in your email service provider

### 3. DMARC
Add DMARC policy to DNS:
```
v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com
```

### 4. Rate Limiting
Implement rate limiting to prevent abuse:
- Max 5 OTP requests per user per hour
- Max 3 failed verification attempts per session

### 5. Monitoring
Monitor email delivery:
- Track delivery rates
- Monitor bounce rates
- Watch for spam complaints

---

## Summary

✅ **Development:** Emails print to console (no setup needed)
✅ **Production:** Configure SMTP with App Password or email service
✅ **Security:** Use environment variables for credentials
✅ **Testing:** Check terminal output for OTP codes

Your OTP login is now working in development mode! 🎉

