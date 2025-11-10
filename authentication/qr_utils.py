import qrcode
import io
import base64
import json
import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import UserQRCode
from products.models import Purchase

def generate_user_qr_data(user):
    """Generate QR data for a user including their purchases"""
    # Get user's pending/awaiting pickup and delivery purchases
    pending_purchases = Purchase.objects.filter(
        buyer=user, 
        status__in=['awaiting_pickup', 'awaiting_delivery']
    ).select_related('product')
    
    # Prepare data for QR code
    qr_data = {
        'user_id': user.id,
        'username': user.username,
        'timestamp': timezone.now().isoformat(),
        'purchases': []
    }
    
    for purchase in pending_purchases:
        qr_data['purchases'].append({
            'id': purchase.id,
            'order_id': purchase.order_id,
            'product_name': purchase.product.title,
            'quantity': purchase.quantity,
            'price': str(purchase.purchase_price),
            'vendor_name': purchase.product.user.username
        })
    
    # Create JWT token that expires in 10 minutes
    token_data = {
        'qr_data': qr_data,
        'exp': datetime.utcnow() + timedelta(minutes=10),
        'iat': datetime.utcnow()
    }
    
    # Use Django secret key for JWT encoding
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm='HS256')
    return token

def create_qr_image(data):
    """Create QR code image from data"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes using a context manager
        with io.BytesIO() as buffer:
            img.save(buffer, format='PNG')
            buffer.seek(0)
            image_content = buffer.getvalue()
            
        # Generate a unique filename that's platform-independent
        filename = f'qr_code_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        return ContentFile(image_content, name=filename)
    except Exception as e:
        print(f"Error creating QR image: {str(e)}")
        import traceback
        traceback.print_exc()
        raise IOError(f"Failed to create QR code image: {str(e)}")

def update_user_qr_code(user):
    """Update or create QR code for user"""
    try:
        qr_data = generate_user_qr_data(user)
        qr_image = create_qr_image(qr_data)
        
        # Get or create user QR code with expires_at set for new records
        expires_at = timezone.now() + timedelta(minutes=10)
        user_qr, created = UserQRCode.objects.get_or_create(
            user=user,
            defaults={'expires_at': expires_at}
        )
        
        # Update the QR code
        # Use a unique filename based on timestamp
        filename = f'qr_{user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.png'
        
        # Clear old image if it exists
        if user_qr.qr_image:
            try:
                user_qr.qr_image.delete(save=False)
            except Exception as e:
                print(f"Warning: Could not delete old QR image: {str(e)}")
        
        # Save new image
        user_qr.qr_data = qr_data
        user_qr.qr_image.save(filename, qr_image, save=False)
        user_qr.expires_at = expires_at
        user_qr.save()
        
        return user_qr
    except Exception as e:
        print(f"Error updating QR code: {str(e)}")
        import traceback
        traceback.print_exc()
        raise IOError(f"Failed to update QR code: {str(e)}")

def decode_qr_data(token):
    """Decode QR code token and return user data"""
    try:
        # Log token info for debugging
        print(f"Decoding QR token of length {len(token)}")
        print(f"Token prefix: {token[:20]}...")
        
        # Check if token looks like a JWT (3 parts separated by dots)
        parts = token.split('.')
        if len(parts) != 3:
            print(f"Token doesn't look like a valid JWT - found {len(parts)} parts instead of 3")
            return {'error': 'Invalid QR code format'}
            
        try:
            # Try to decode the JWT
            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Validate expected structure
            if 'qr_data' not in decoded_data:
                print("JWT decoded but missing 'qr_data' key")
                return {'error': 'QR data structure is invalid'}
            
            print("=================== Successfully decoded QR token =====================")
            print(decoded_data['qr_data'])
            return decoded_data['qr_data']
        except jwt.ExpiredSignatureError:
            print("JWT signature has expired")
            return {'error': 'QR code has expired'}
        except jwt.InvalidTokenError as e:
            print(f"Invalid JWT token: {str(e)}")
            return {'error': 'Invalid QR code signature'}
    except Exception as e:
        print(f"Unexpected error decoding QR token: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': f'Error processing QR code: {str(e)}'}

def get_user_purchases_from_qr(qr_data):
    """Extract purchase information from QR data"""
    if 'error' in qr_data:
        return qr_data
    
    user_id = qr_data.get('user_id')
    purchases_data = qr_data.get('purchases', [])
    
    return {
        'user_id': user_id,
        'username': qr_data.get('username'),
        'purchases': purchases_data,
        'timestamp': qr_data.get('timestamp')
    }
