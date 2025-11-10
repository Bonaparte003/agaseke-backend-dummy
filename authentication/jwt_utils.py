"""
JWT Token Utilities for Authentication
"""
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model

User = get_user_model()


def get_tokens_for_user(user):
    """
    Generate access and refresh tokens for a user
    
    Args:
        user: User instance
        
    Returns:
        dict: {
            'access': str,  # Access token
            'refresh': str,  # Refresh token
        }
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def refresh_access_token(refresh_token):
    """
    Refresh an access token using a refresh token
    
    Args:
        refresh_token: Refresh token string
        
    Returns:
        dict: {
            'access': str,  # New access token
        }
    Raises:
        TokenError: If refresh token is invalid or expired
    """
    try:
        refresh = RefreshToken(refresh_token)
        return {
            'access': str(refresh.access_token),
        }
    except TokenError as e:
        raise InvalidToken(f"Invalid refresh token: {str(e)}")


def get_user_from_token(token):
    """
    Get user from JWT access token
    
    Args:
        token: JWT access token string
        
    Returns:
        User: User instance or None if invalid
    """
    try:
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from django.conf import settings
        import jwt
        
        # Decode token
        decoded_data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        # Get user ID from token
        user_id = decoded_data.get('user_id')
        if not user_id:
            return None
        
        # Get user
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            return None
            
    except (InvalidToken, TokenError, jwt.DecodeError, jwt.ExpiredSignatureError):
        return None

