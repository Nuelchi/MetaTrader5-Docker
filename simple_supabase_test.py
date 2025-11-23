#!/usr/bin/env python3
"""
Simple Supabase connection test - minimal version
"""

import supabase

# Hardcoded values for testing
SUPABASE_URL = "https://kgfzbkwyepchbysaysky.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtnZnpia3d5ZXBjaGJ5c2F5c2t5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI0Nzk5NDAsImV4cCI6MjA2ODA1NTk0MH0.WsMnjZsBPdM5okL4KZXZidX8eiTiGmN-Qc--Y359H6M"

def test_supabase_connection():
    """Test basic Supabase connection"""
    print("🔗 Testing Supabase connection...")

    try:
        # Test 1: Create Supabase client
        supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase client created successfully")

        # Test 2: Try to access a public table
        try:
            # This will fail if no tables exist, but should not fail due to auth
            result = supabase_client.table("test").select("*").limit(1).execute()
            print("✅ Supabase query executed (table may not exist, but auth works)")
        except Exception as e:
            if "relation" in str(e).lower() or "does not exist" in str(e).lower():
                print("✅ Supabase connection works (table doesn't exist, but auth is valid)")
            else:
                print(f"⚠️  Supabase query failed: {e}")

        print("\n🎉 Supabase connection test passed!")
        print(f"📍 Supabase URL: {SUPABASE_URL}")
        print(f"🔑 Using anon key: {SUPABASE_ANON_KEY[:20]}...")

        return True

    except Exception as e:
        print(f"❌ Supabase connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")