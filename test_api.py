#!/usr/bin/env python3
"""
agaseke API Test Script

This script demonstrates how to use the agaseke REST API endpoints.
Make sure to run the Django server first: python manage.py runserver
"""

import requests
import json
from typing import Dict, Any

class agasekeAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        
    def get_csrf_token(self):
        """Get CSRF token for authenticated requests"""
        response = self.session.get(f"{self.base_url}/auth/login/")
        # Extract CSRF token from the response (simplified)
        self.csrf_token = "dummy_csrf_token"  # In real implementation, parse from response
        
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user"""
        url = f"{self.base_url}/auth/api/rest/auth/register/"
        response = self.session.post(url, json=user_data)
        return response.json()
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login user"""
        url = f"{self.base_url}/auth/api/rest/auth/login/"
        data = {"username": username, "password": password}
        response = self.session.post(url, json=data)
        return response.json()
    
    def logout_user(self) -> Dict[str, Any]:
        """Logout user"""
        url = f"{self.base_url}/auth/api/rest/auth/logout/"
        response = self.session.post(url)
        return response.json()
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        url = f"{self.base_url}/auth/api/rest/users/me/"
        response = self.session.get(url)
        return response.json()
    
    def create_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new post/product"""
        url = f"{self.base_url}/auth/api/rest/posts/"
        # For file uploads, you would use files parameter
        response = self.session.post(url, json=post_data)
        return response.json()
    
    def get_posts(self, **filters) -> Dict[str, Any]:
        """Get all posts with optional filters"""
        url = f"{self.base_url}/auth/api/rest/posts/"
        response = self.session.get(url, params=filters)
        return response.json()
    
    def like_post(self, post_id: int) -> Dict[str, Any]:
        """Like/unlike a post"""
        url = f"{self.base_url}/auth/api/rest/posts/{post_id}/like/"
        response = self.session.post(url)
        return response.json()
    
    def bookmark_post(self, post_id: int) -> Dict[str, Any]:
        """Bookmark/unbookmark a post"""
        url = f"{self.base_url}/auth/api/rest/posts/{post_id}/bookmark/"
        response = self.session.post(url)
        return response.json()
    
    def purchase_product(self, post_id: int, purchase_data: Dict[str, Any]) -> Dict[str, Any]:
        """Purchase a product"""
        url = f"{self.base_url}/auth/api/rest/posts/{post_id}/purchase/"
        response = self.session.post(url, json=purchase_data)
        return response.json()
    
    def add_review(self, post_id: int, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a product review"""
        url = f"{self.base_url}/auth/api/rest/posts/{post_id}/add_review/"
        response = self.session.post(url, json=review_data)
        return response.json()
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        url = f"{self.base_url}/auth/api/rest/dashboard/stats/"
        response = self.session.get(url)
        return response.json()
    
    def get_purchases(self, **filters) -> Dict[str, Any]:
        """Get user purchases"""
        url = f"{self.base_url}/auth/api/rest/purchases/"
        response = self.session.get(url, params=filters)
        return response.json()
    
    def get_bookmarks(self) -> Dict[str, Any]:
        """Get user bookmarks"""
        url = f"{self.base_url}/auth/api/rest/bookmarks/"
        response = self.session.get(url)
        return response.json()


def main():
    """Demonstrate API usage"""
    client = agasekeAPIClient()
    
    print("🚀 agaseke API Test Script")
    print("=" * 50)
    
    # Test user registration
    print("\n1. Testing User Registration...")
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "phone_number": "+250123456789",
        "password": "testpassword123",
        "password_confirm": "testpassword123"
    }
    
    try:
        register_response = client.register_user(user_data)
        print(f"✅ Registration Response: {register_response}")
    except Exception as e:
        print(f"❌ Registration Error: {e}")
    
    # Test user login
    print("\n2. Testing User Login...")
    try:
        login_response = client.login_user("testuser", "testpassword123")
        print(f"✅ Login Response: {login_response}")
    except Exception as e:
        print(f"❌ Login Error: {e}")
    
    # Test getting user profile
    print("\n3. Testing Get User Profile...")
    try:
        profile_response = client.get_user_profile()
        print(f"✅ Profile Response: {profile_response}")
    except Exception as e:
        print(f"❌ Profile Error: {e}")
    
    # Test creating a post
    print("\n4. Testing Create Post...")
    post_data = {
        "title": "Test Product",
        "description": "This is a test product description",
        "price": "99.99",
        "category": "electronics",
        "inventory": 10
    }
    
    try:
        post_response = client.create_post(post_data)
        print(f"✅ Post Creation Response: {post_response}")
    except Exception as e:
        print(f"❌ Post Creation Error: {e}")
    
    # Test getting posts
    print("\n5. Testing Get Posts...")
    try:
        posts_response = client.get_posts()
        print(f"✅ Posts Response: {posts_response}")
    except Exception as e:
        print(f"❌ Posts Error: {e}")
    
    # Test dashboard stats
    print("\n6. Testing Dashboard Stats...")
    try:
        stats_response = client.get_dashboard_stats()
        print(f"✅ Dashboard Stats Response: {stats_response}")
    except Exception as e:
        print(f"❌ Dashboard Stats Error: {e}")
    
    # Test logout
    print("\n7. Testing User Logout...")
    try:
        logout_response = client.logout_user()
        print(f"✅ Logout Response: {logout_response}")
    except Exception as e:
        print(f"❌ Logout Error: {e}")
    
    print("\n🎉 API Test Complete!")
    print("\nTo run the full test, make sure:")
    print("1. Django server is running: python manage.py runserver")
    print("2. Database is set up: python manage.py migrate")
    print("3. All dependencies are installed: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
