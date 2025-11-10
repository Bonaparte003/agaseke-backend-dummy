"""
JWT Authentication Decorators
"""
from functools import wraps
from django.http import JsonResponse
from .jwt_utils import get_user_from_token


def jwt_required(view_func):
    """
    Decorator to require JWT authentication for a view
    
    Usage:
        @jwt_required
        def my_api_view(request):
            user = request.user  # User is attached to request
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({
                'success': False,
                'message': 'Authentication required',
                'errors': {'auth': ['Please provide a valid JWT token in Authorization header']}
            }, status=401)
        
        token = auth_header.replace('Bearer ', '')
        user = get_user_from_token(token)
        
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'Invalid or expired token',
                'errors': {'auth': ['Invalid or expired JWT token']}
            }, status=401)
        
        # Attach user to request for use in view
        request.user = user
        return view_func(request, *args, **kwargs)
    
    return wrapper


def jwt_optional(view_func):
    """
    Decorator to optionally authenticate with JWT (doesn't fail if no token)
    
    Usage:
        @jwt_optional
        def my_api_view(request):
            if request.user:  # User may be None if no token
                # Authenticated user
            else:
                # Anonymous user
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Try to get user from token, but don't fail if not present
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            user = get_user_from_token(token)
            request.user = user if user else None
        else:
            request.user = None
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

