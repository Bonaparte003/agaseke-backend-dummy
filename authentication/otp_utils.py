import random
import string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTPVerification

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(user, otp_code, purpose='purchase_confirmation'):
    """Send OTP via email with beautiful HTML template"""
    subject = '🔐 agaseke - Your Verification Code'
    
    # Create HTML email template
    if purpose == 'purchase_confirmation':
        email_title = "Purchase Verification Required"
        email_subtitle = "Please verify your identity to complete your purchase pickup"
        action_text = "complete your purchase pickup"
    else:
        email_title = "Verification Required"
        email_subtitle = "Please verify your identity"
        action_text = "continue with your action"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>agaseke Verification</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 8px;
            }}
            .header p {{
                font-size: 16px;
                opacity: 0.9;
                margin-bottom: 0;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .greeting {{
                font-size: 18px;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 20px;
            }}
            .message {{
                font-size: 16px;
                color: #555;
                margin-bottom: 30px;
                line-height: 1.7;
            }}
            .otp-container {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                border-radius: 12px;
                padding: 30px;
                text-align: center;
                margin: 30px 0;
                border: 3px dashed #fff;
                position: relative;
            }}
            .otp-label {{
                color: white;
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 15px;
                opacity: 0.9;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: 800;
                color: white;
                letter-spacing: 8px;
                margin: 0;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                font-family: 'Courier New', monospace;
            }}
            .expiry-notice {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 15px 20px;
                margin: 25px 0;
                color: #856404;
                font-size: 14px;
                display: flex;
                align-items: center;
            }}
            .expiry-notice::before {{
                content: "⏰";
                font-size: 18px;
                margin-right: 10px;
            }}
            .security-notice {{
                background-color: #e8f4fd;
                border: 1px solid #b6d7ff;
                border-radius: 8px;
                padding: 15px 20px;
                margin: 25px 0;
                color: #0c5460;
                font-size: 14px;
                display: flex;
                align-items: center;
            }}
            .security-notice::before {{
                content: "🔒";
                font-size: 18px;
                margin-right: 10px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e9ecef;
            }}
            .footer p {{
                color: #6c757d;
                font-size: 14px;
                margin-bottom: 10px;
            }}
            .brand {{
                color: #667eea;
                font-weight: 700;
                font-size: 16px;
                text-decoration: none;
            }}
            .divider {{
                height: 1px;
                background: linear-gradient(to right, transparent, #e9ecef, transparent);
                margin: 25px 0;
            }}
            @media (max-width: 600px) {{
                .email-container {{
                    margin: 10px;
                    border-radius: 8px;
                }}
                .header, .content, .footer {{
                    padding: 25px 20px;
                }}
                .otp-code {{
                    font-size: 28px;
                    letter-spacing: 4px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>🛡️ agaseke</h1>
                <p>{email_title}</p>
            </div>
            
            <div class="content">
                <div class="greeting">Hello {user.first_name or user.username}! 👋</div>
                
                <div class="message">
                    {email_subtitle}. We've generated a secure verification code for you to {action_text}.
                </div>
                
                <div class="otp-container">
                    <div class="otp-label">Your Verification Code</div>
                    <div class="otp-code">{otp_code}</div>
                </div>
                
                <div class="expiry-notice">
                    This verification code will expire in <strong>5 minutes</strong> for your security.
                </div>
                
                <div class="security-notice">
                    If you didn't request this verification code, please ignore this email. Never share your verification codes with anyone.
                </div>
                
                <div class="divider"></div>
                
                <div class="message">
                    Need help? Feel free to contact our support team. We're here to assist you!
                </div>
            </div>
            
            <div class="footer">
                <p>This email was sent by <a href="#" class="brand">agaseke</a></p>
                <p>Your trusted marketplace for secure transactions</p>
                <p style="margin-top: 15px; font-size: 12px; color: #868e96;">
                    © 2025 agaseke. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version for email clients that don't support HTML
    text_content = f"""
    agaseke - {email_title}
    
    Hello {user.first_name or user.username}!
    
    {email_subtitle}. Your verification code is:
    
    {otp_code}
    
    This code will expire in 5 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    agaseke Team
    """
    
    try:
        # Create email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False

def create_otp(user, purpose='purchase_confirmation'):
    """Create and send OTP to user"""
    # Invalidate any existing unused OTPs for this user and purpose
    OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False
    ).update(is_used=True)
    
    # Generate new OTP
    otp_code = generate_otp()
    
    # Create OTP record
    otp = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=5)
    )
    
    # Send OTP via email
    email_sent = send_otp_email(user, otp_code, purpose)
    
    return {
        'otp_id': otp.id,
        'email_sent': email_sent,
        'expires_at': otp.expires_at
    }

def verify_otp(user, otp_code, purpose='purchase_confirmation'):
    """Verify OTP code"""
    try:
        otp = OTPVerification.objects.get(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            is_used=False
        )
        
        if otp.is_expired():
            return {'valid': False, 'error': 'OTP has expired'}
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        return {'valid': True, 'otp_id': otp.id}
    
    except OTPVerification.DoesNotExist:
        return {'valid': False, 'error': 'Invalid OTP code'}

def cleanup_expired_otps():
    """Clean up expired OTPs (can be run as a cron job)"""
    expired_otps = OTPVerification.objects.filter(
        expires_at__lt=timezone.now()
    )
    count = expired_otps.count()
    expired_otps.delete()
    return count
