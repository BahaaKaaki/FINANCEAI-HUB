#!/usr/bin/env python3
"""
Complete setup script for AI Financial Data System.

This script handles:
1. Database initialization
2. Sample data creation
3. System verification
4. Postman collection setup instructions
"""

import sys
import subprocess
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def run_command(command: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"❌ {description} failed:")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed: {str(e)}")
        return False

def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    print("📋 Checking dependencies...")
    
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        print("✅ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {str(e)}")
        print("   Run: pip install -r requirements.txt")
        return False

def setup_database() -> bool:
    """Initialize database with tables and sample data."""
    print("🗄️  Setting up database...")
    
    try:
        from app.core.logging import setup_logging, get_logger
        from app.database.connection import create_tables, check_database_connection
        
        setup_logging()
        logger = get_logger(__name__)
        
        # Check connection
        if not check_database_connection():
            print("❌ Cannot connect to database")
            return False
        
        # Create tables
        create_tables()
        print("✅ Database tables created")
        
        # Create sample data
        from init_database import create_sample_data
        if create_sample_data():
            print("✅ Sample data created")
        else:
            print("⚠️  Sample data creation failed (tables still created)")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False

def verify_system() -> bool:
    """Verify the system is working correctly."""
    print("🔍 Verifying system...")
    
    try:
        # Test basic imports
        from app.main import app
        from app.database.connection import check_database_connection
        
        # Test database
        if not check_database_connection():
            print("❌ Database verification failed")
            return False
        
        print("✅ System verification passed")
        return True
        
    except Exception as e:
        print(f"❌ System verification failed: {str(e)}")
        return False

def print_next_steps():
    """Print instructions for next steps."""
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\n📋 NEXT STEPS:")
    print("\n1. 🚀 Start the API server:")
    print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    
    print("\n2. 🧪 Test the system:")
    print("   python test_api_endpoints.py")
    
    print("\n3. 📱 Use Postman collection:")
    print("   - Import: AI_Financial_System_Complete_Collection.json")
    print("   - Import: AI_Financial_System_Environment.json")
    print("   - Select the environment and start testing!")
    
    print("\n4. 🌐 Access API documentation:")
    print("   http://localhost:8000/docs")
    
    print("\n📊 SAMPLE DATA AVAILABLE:")
    print("   - 3 financial records (QuickBooks & Rootfi)")
    print("   - 3 sample accounts")
    print("   - Ready for natural language queries!")
    
    print("\n🔧 TROUBLESHOOTING:")
    print("   - If tables are missing: python fix_database_tables.py")
    print("   - For full reset: python init_database.py --reset --sample-data")
    print("   - Check logs for detailed error information")

def main():
    """Main setup function."""
    print("🚀 AI Financial Data System - Complete Setup")
    print("=" * 60)
    print("This script will set up your system for first use.\n")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        print("   Install them with: pip install -r requirements.txt")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("\n❌ Setup failed: Database initialization error")
        sys.exit(1)
    
    # Verify system
    if not verify_system():
        print("\n❌ Setup failed: System verification error")
        sys.exit(1)
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()