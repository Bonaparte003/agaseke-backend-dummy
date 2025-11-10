"""
Helper functions to serialize models to JSON for API responses
"""
from decimal import Decimal
from django.db.models import Avg
from posts.models import Post, ProductReview, Bookmark
from products.models import Purchase, ProductImage
from users.models import User


def serialize_post(post, user=None):
    """Serialize a Post object to JSON"""
    # Get auxiliary images
    auxiliary_images = ProductImage.objects.filter(product=post).order_by('display_order')
    aux_images_data = [{
        'id': img.id,
        'image_url': img.image.url if img.image else None,
        'display_order': img.display_order
    } for img in auxiliary_images]
    
    # Calculate average rating
    reviews = ProductReview.objects.filter(product=post)
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    avg_rating = round(avg_rating, 1) if avg_rating else None
    
    # Check if bookmarked/liked by user
    is_bookmarked = False
    is_liked = False
    if user:
        is_bookmarked = Bookmark.objects.filter(user=user, post=post).exists()
        is_liked = user in post.likes.all()
    
    return {
        'id': post.id,
        'title': post.title,
        'description': post.description,
        'price': float(post.price) if post.price else None,
        'category': post.category,
        'category_display': post.get_category_display(),
        'inventory': post.inventory,
        'created_at': post.created_at.isoformat(),
        'updated_at': post.updated_at.isoformat(),
        'total_purchases': post.total_purchases,
        'image_url': post.image.url if post.image else None,
        'auxiliary_images': aux_images_data,
        'average_rating': avg_rating,
        'review_count': reviews.count(),
        'total_likes': post.total_likes(),
        'is_bookmarked': is_bookmarked,
        'is_liked': is_liked,
        'is_sold_out': post.is_sold_out(),
        'vendor': {
            'id': post.user.id,
            'username': post.user.username,
            'first_name': post.user.first_name,
            'last_name': post.user.last_name,
            'is_vendor_role': post.user.is_vendor_role,
            'profile_picture_url': post.user.profile_picture.url if post.user.profile_picture else None
        }
    }


def serialize_purchase(purchase):
    """Serialize a Purchase object to JSON"""
    return {
        'id': purchase.id,
        'order_id': purchase.order_id,
        'product': serialize_post(purchase.product) if purchase.product else None,
        'quantity': purchase.quantity,
        'purchase_price': float(purchase.purchase_price) if purchase.purchase_price else None,
        'status': purchase.status,
        'status_display': purchase.get_status_display(),
        'delivery_method': purchase.delivery_method,
        'delivery_method_display': purchase.get_delivery_method_display(),
        'payment_method': purchase.payment_method,
        'payment_method_display': purchase.get_payment_method_display(),
        'delivery_fee': float(purchase.delivery_fee) if purchase.delivery_fee else None,
        'delivery_address': purchase.delivery_address,
        'delivery_latitude': float(purchase.delivery_latitude) if purchase.delivery_latitude else None,
        'delivery_longitude': float(purchase.delivery_longitude) if purchase.delivery_longitude else None,
        'created_at': purchase.created_at.isoformat(),
        'updated_at': purchase.updated_at.isoformat(),
        'buyer': {
            'id': purchase.buyer.id,
            'username': purchase.buyer.username,
            'first_name': purchase.buyer.first_name,
            'last_name': purchase.buyer.last_name,
            'email': purchase.buyer.email,
        },
        'vendor_payment_amount': float(purchase.vendor_payment_amount) if purchase.vendor_payment_amount else None,
        'agaseke_commission_amount': float(purchase.agaseke_commission_amount) if purchase.agaseke_commission_amount else None,
        'pickup_confirmed_at': purchase.pickup_confirmed_at.isoformat() if purchase.pickup_confirmed_at else None,
        'agaseke_user': {
            'id': purchase.agaseke_user.id,
            'username': purchase.agaseke_user.username,
        } if purchase.agaseke_user else None,
    }


def serialize_review(review):
    """Serialize a ProductReview object to JSON"""
    return {
        'id': review.id,
        'rating': review.rating,
        'comment': review.comment,
        'created_at': review.created_at.isoformat(),
        'updated_at': review.updated_at.isoformat(),
        'reviewer': {
            'id': review.reviewer.id,
            'username': review.reviewer.username,
            'first_name': review.reviewer.first_name,
            'last_name': review.reviewer.last_name,
            'profile_picture_url': review.reviewer.profile_picture.url if review.reviewer.profile_picture else None,
        }
    }


def serialize_bookmark(bookmark):
    """Serialize a Bookmark object to JSON"""
    return {
        'id': bookmark.id,
        'created_at': bookmark.created_at.isoformat(),
        'post': serialize_post(bookmark.post)
    }


def serialize_user(user):
    """Serialize a User object to JSON"""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'is_vendor_role': user.is_vendor_role,
        'phone_number': user.phone_number or '',
        'profile_picture_url': user.profile_picture.url if user.profile_picture else None,
        'total_sales': float(user.total_sales) if user.total_sales else 0.0,
        'total_purchases': float(user.total_purchases) if user.total_purchases else 0.0,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }

