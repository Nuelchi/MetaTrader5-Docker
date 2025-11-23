#!/usr/bin/env python3
"""
Test JWT token verification with the provided token
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from auth import auth_verifier

# JWT token from user's frontend login
TEST_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IllTcHdzeW44YVMwdTRNWFMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2tnZnpia3d5ZXBjaGJ5c2F5c2t5LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIwYjNlMTY1Yy0yNjYxLTQ2NWYtODFiYS1jYjVlOWU0YWJjNjEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYzODkyMzcxLCJpYXQiOjE3NjM4ODg3NzEsImVtYWlsIjoiZG94YWZvcmV4NTVAZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImRveGFmb3JleDU1QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjBiM2UxNjVjLTI2NjEtNDY1Zi04MWJhLWNiNWU5ZTRhYmM2MSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzYzODIzOTk0fV0sInNlc3Npb25faWQiOiI5NWEyZDNmOS00YmJhLTRhZWMtOWIyYi02NmRmMDVkY2RkNzIiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.TrOX4VDjeVFdPeDZimoyD1AeWLuQq_yAhOS43OdmaHo"

def test_jwt_verification():
    """Test JWT token verification with the provided token"""
    print("🔐 Testing JWT token verification...")
    print(f"📍 Supabase URL: {settings.supabase_url}")
    print(f"🔑 Using anon key: {settings.supabase_anon_key[:20]}...")
    print(f"🎫 Testing token: {TEST_JWT_TOKEN[:50]}...")

    try:
        # Test 1: Verify JWT token
        print("\n1️⃣ Testing JWT token verification...")
        payload = auth_verifier.verify_jwt_token(TEST_JWT_TOKEN)

        if payload:
            print("✅ JWT token verified successfully!")
            print(f"   📧 Email: {payload.get('email', 'N/A')}")
            print(f"   🆔 User ID: {payload.get('sub', 'N/A')}")
            print(f"   🎭 Role: {payload.get('role', 'N/A')}")
            print(f"   ⏰ Issued: {payload.get('iat', 'N/A')}")
            print(f"   ⏰ Expires: {payload.get('exp', 'N/A')}")
        else:
            print("❌ JWT token verification failed!")
            return False

        # Test 2: Get user from token
        print("\n2️⃣ Testing user extraction from token...")
        user = auth_verifier.get_user_from_token(TEST_JWT_TOKEN)

        if user:
            print("✅ User extracted successfully!")
            print(f"   👤 User ID: {user.get('user_id', 'N/A')}")
            print(f"   📧 Email: {user.get('email', 'N/A')}")
            print(f"   🎭 Role: {user.get('role', 'N/A')}")
            print(f"   📅 Created: {user.get('created_at', 'N/A')}")
            print(f"   🔑 Last Sign In: {user.get('last_sign_in_at', 'N/A')}")
        else:
            print("❌ User extraction failed!")
            return False

        print("\n🎉 All JWT verification tests passed!")
        print("✅ MT5 server can authenticate users from your frontend!")

        return True

    except Exception as e:
        print(f"❌ JWT verification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_jwt_verification()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)