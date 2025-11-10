#!/usr/bin/env python3
"""
agaseke API Setup Script

This script helps set up the agaseke API by:
1. Installing required dependencies
2. Running database migrations
3. Creating a superuser (optional)
4. Testing the API endpoints
"""

import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def setup_django():
    """Setup Django environment"""
    print("🔄 Setting up Django environment...")
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agaseke.settings')
    
    # Setup Django
    django.setup()
    
    print("✅ Django environment setup complete")

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    commands = [
        ("pip install -r requirements.txt", "Installing Python packages"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"❌ Failed to {description.lower()}")
            return False
    
    return True

def run_migrations():
    """Run Django database migrations"""
    print("🗄️ Running database migrations...")
    
    try:
        execute_from_command_line(['manage.py', 'makemigrations'])
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Database migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def create_superuser():
    """Create a Django superuser"""
    print("👤 Creating superuser...")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            print("✅ Superuser already exists")
            return True
        
        # Create superuser
        username = "admin"
        email = "admin@agaseke.com"
        password = "admin123"
        
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='agaseke'
        )
        
        print(f"✅ Superuser created successfully")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create superuser: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("🧪 Testing API endpoints...")
    
    try:
        # Import and run the test script
        from test_api import main
        main()
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 agaseke API Setup")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Setup steps
    steps = [
        (install_dependencies, "Install dependencies"),
        (setup_django, "Setup Django environment"),
        (run_migrations, "Run database migrations"),
        (create_superuser, "Create superuser"),
    ]
    
    for step_func, step_name in steps:
        print(f"\n📋 {step_name}")
        if not step_func():
            print(f"❌ Setup failed at: {step_name}")
            return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Access the API at: http://localhost:8000/auth/api/rest/")
    print("3. Access the browsable API at: http://localhost:8000/auth/api/rest/")
    print("4. Access the admin panel at: http://localhost:8000/admin/")
    print("5. Run the test script: python test_api.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
