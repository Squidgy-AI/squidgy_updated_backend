#!/usr/bin/env python3
"""
Setup Business Database Schema
Run this first to create the business_information table
"""

import asyncio
import os
from dotenv import load_dotenv

try:
    from database import execute
    DATABASE_AVAILABLE = True
except ImportError:
    print("❌ Database module not available")
    DATABASE_AVAILABLE = False

load_dotenv()

async def setup_database():
    """Setup the business database schema"""
    
    if not DATABASE_AVAILABLE:
        print("❌ Database not available. Please check your database.py file.")
        return False
    
    try:
        print("🗄️  Setting up business database schema...")
        
        # Read and execute the SQL schema
        with open("business_setup_complete_schema.sql", "r") as f:
            schema_sql = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"   📝 Executing statement {i}/{len(statements)}...")
                await execute(statement + ';')
        
        print("✅ Database schema setup completed!")
        print("   📋 Table: squidgy_business_information")
        print("   📊 View: business_setup_status")
        print("   🔍 Indexes and constraints created")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

async def verify_database():
    """Verify the database setup"""
    
    try:
        print("\n🔍 Verifying database setup...")
        
        # Check if table exists
        result = await execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'squidgy_business_information'
        """)
        
        if result:
            print("✅ Table 'squidgy_business_information' exists")
        else:
            print("❌ Table 'squidgy_business_information' not found")
            return False
        
        # Check view
        result = await execute("""
            SELECT table_name FROM information_schema.views 
            WHERE table_schema = 'public' AND table_name = 'business_setup_status'
        """)
        
        if result:
            print("✅ View 'business_setup_status' exists")
        else:
            print("❌ View 'business_setup_status' not found")
        
        print("✅ Database verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False

async def main():
    """Main setup function"""
    
    print("="*60)
    print("🚀 BUSINESS SETUP DATABASE INITIALIZATION")
    print("="*60)
    
    # Setup database
    setup_success = await setup_database()
    
    if setup_success:
        # Verify setup
        verify_success = await verify_database()
        
        if verify_success:
            print("\n🎉 DATABASE SETUP COMPLETE!")
            print("You can now run the business setup API:")
            print("   python3 business_setup_complete_api.py")
            print("   python3 test_business_setup_complete.py")
        else:
            print("\n❌ Database verification failed")
    else:
        print("\n❌ Database setup failed")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())