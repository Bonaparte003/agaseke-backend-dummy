import random
import string
import uuid
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTPVerification

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(user, otp_code, purpose='purchase_confirmation'):
    """Send OTP via email"""
    subject = 'Agaseke - Your Verification Code'
    
    # Create HTML email template
    if purpose == 'purchase_confirmation':
        email_title = "Purchase Verification Required"
        email_subtitle = "Please verify your identity to complete your purchase pickup"
        action_text = "complete your purchase pickup"
    elif purpose == 'login':
        email_title = "Login Verification Required"
        email_subtitle = "Please verify your identity to complete your login"
        action_text = "complete your login"
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
        <title>Agaseke Verification</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #1a1a1a;
                background-color: #f4f6f8;
                padding: 20px 0;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            }}
            .header {{
                background-color: #667eea;
                color: white;
                padding: 32px 40px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 6px;
                letter-spacing: -0.5px;
            }}
            .header p {{
                font-size: 15px;
                opacity: 0.95;
                margin-bottom: 0;
                font-weight: 400;
            }}
            .content {{
                padding: 40px 40px 32px;
            }}
            .greeting {{
                font-size: 16px;
                font-weight: 600;
                color: #1a1a1a;
                margin-bottom: 16px;
            }}
            .message {{
                font-size: 15px;
                color: #4a5568;
                margin-bottom: 32px;
                line-height: 1.6;
            }}
            .otp-section {{
                background-color: #f8f9fa;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 24px;
                text-align: center;
                margin: 32px 0;
            }}
            .otp-label {{
                color: #718096;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: 700;
                color: #667eea;
                letter-spacing: 10px;
                margin: 12px 0;
                font-family: 'Courier New', Consolas, Monaco, monospace;
                user-select: all;
                -webkit-user-select: all;
                -moz-user-select: all;
                -ms-user-select: all;
                cursor: text;
                padding: 8px 16px;
                background-color: #ffffff;
                border-radius: 4px;
                display: inline-block;
                border: 1px solid #cbd5e0;
            }}
            .otp-helper {{
                font-size: 13px;
                color: #718096;
                margin-top: 12px;
                font-style: italic;
            }}
            .info-box {{
                background-color: #fef3c7;
                border-left: 4px solid #f59e0b;
                border-radius: 4px;
                padding: 16px 20px;
                margin: 24px 0;
                font-size: 14px;
                color: #92400e;
            }}
            .info-box strong {{
                font-weight: 600;
            }}
            .security-box {{
                background-color: #dbeafe;
                border-left: 4px solid #3b82f6;
                border-radius: 4px;
                padding: 16px 20px;
                margin: 24px 0;
                font-size: 14px;
                color: #1e40af;
            }}
            .divider {{
                height: 1px;
                background-color: #e2e8f0;
                margin: 32px 0;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 32px 40px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
            }}
            .footer p {{
                color: #718096;
                font-size: 14px;
                margin-bottom: 8px;
                line-height: 1.5;
            }}
            .brand {{
                color: #667eea;
                font-weight: 600;
                text-decoration: none;
            }}
            .copyright {{
                margin-top: 16px;
                font-size: 12px;
                color: #a0aec0;
            }}
            @media (max-width: 600px) {{
                .email-container {{
                    margin: 0 10px;
                    border-radius: 6px;
                }}
                .header, .content, .footer {{
                    padding: 24px 20px;
                }}
                .otp-code {{
                    font-size: 28px;
                    letter-spacing: 8px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>Agaseke</h1>
                <p>{email_title}</p>
            </div>
            
            <div class="content">
                <div class="greeting">Hello {user.first_name or user.username},</div>
                
                <div class="message">
                    {email_subtitle}. We've generated a secure verification code for you to {action_text}.
                </div>
                
                <div class="otp-section">
                    <div class="otp-label">Your Verification Code</div>
                    <div class="otp-code">{otp_code}</div>
                    <div class="otp-helper">Click or tap to select and copy</div>
                </div>
                
                <div class="info-box">
                    <strong>Important:</strong> This verification code will expire in 5 minutes for your security.
                </div>
                
                <div class="security-box">
                    <strong>Security Notice:</strong> If you didn't request this verification code, please ignore this email. Never share your verification codes with anyone.
                </div>
                
                <div class="divider"></div>
                
                <div class="message">
                    If you need assistance, please contact our support team. We're here to help!
                </div>
            </div>
            
            <div class="footer">
                <p>This email was sent by <a href="#" class="brand">Agaseke</a></p>
                <p>Your trusted marketplace for secure transactions</p>
                <p class="copyright">© 2025 Agaseke. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version for email clients that don't support HTML
    text_content = f"""
Agaseke - {email_title}

Hello {user.first_name or user.username},

{email_subtitle}. Your verification code is:

{otp_code}

IMPORTANT: This code will expire in 5 minutes.

SECURITY NOTICE: If you didn't request this code, please ignore this email. Never share your verification codes with anyone.

If you need assistance, please contact our support team.

Best regards,
Agaseke Team

---
© 2025 Agaseke. All rights reserved.
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

def create_otp(user, purpose='purchase_confirmation', session_id=None):
    """Create and send OTP to user"""
    # Invalidate any existing unused OTPs for this user and purpose
    OTPVerification.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False
    ).update(is_used=True)
    
    # Generate new OTP
    otp_code = generate_otp()
    
    # Generate session_id if not provided (for login OTP)
    if purpose == 'login' and not session_id:
        session_id = str(uuid.uuid4())
    
    # Create OTP record
    otp = OTPVerification.objects.create(
        user=user,
        otp_code=otp_code,
        purpose=purpose,
        session_id=session_id,
        expires_at=timezone.now() + timedelta(minutes=5)
    )
    
    # Send OTP via email
    email_sent = send_otp_email(user, otp_code, purpose)
    
    return {
        'otp_id': otp.id,
        'session_id': session_id,
        'email_sent': email_sent,
        'expires_at': otp.expires_at
    }

def verify_otp(user, otp_code, purpose='purchase_confirmation', session_id=None):
    """Verify OTP code"""
    try:
        # Build query filters
        filters = {
            'user': user,
            'otp_code': otp_code,
            'purpose': purpose,
            'is_used': False
        }
        
        # Add session_id filter if provided (for login OTP)
        if session_id:
            filters['session_id'] = session_id
        
        otp = OTPVerification.objects.get(**filters)
        
        if otp.is_expired():
            return {'valid': False, 'error': 'OTP has expired'}
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        return {'valid': True, 'otp_id': otp.id, 'user': user}
    
    except OTPVerification.DoesNotExist:
        return {'valid': False, 'error': 'Invalid OTP code or session'}

def cleanup_expired_otps():
    """Clean up expired OTPs (can be run as a cron job)"""
    expired_otps = OTPVerification.objects.filter(
        expires_at__lt=timezone.now()
    )
    count = expired_otps.count()
    expired_otps.delete()
    return count
