#!/usr/bin/env python3
"""
Test real JWT token verification using Supabase client (same as backend)
"""

import supabase

# Your real JWT token from frontend login
REAL_JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IllTcHdzeW44YVMwdTRNWFMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2tnZnpia3d5ZXBjaGJ5c2F5c2t5LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIwYjNlMTY1Yy0yNjYxLTQ2NWYtODFiYS1jYjVlOWU0YWJjNjEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzYzODk3NjM1LCJpYXQiOjE3NjM4OTQwMzUsImVtYWlsIjoiZG94YWZvcmV4NTVAZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6ImRveGFmb3JleDU1QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjBiM2UxNjVjLTI2NjEtNDY1Zi04MWJhLWNiNWU5ZTRhYmM2MSJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzYzODIzOTk0fV0sInNlc3Npb25faWQiOiI5NWEyZDNmOS00YmJhLTRhZWMtOWIyYi02NmRmMDVkY2RkNzIiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.lx50m8PIg1kSH71d4TpY6-24MLCO-xgqA93yf7TaY-w"

# Supabase configuration (same as backend)
SUPABASE_URL = "https://kgfzbkwyepchbysaysky.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtnZnpia3d5ZXBjaGJ5c2F5c2t5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI0Nzk5NDAsImV4cCI6MjA2ODA1NTk0MH0.WsMnjZsBPdM5okL4KZXZidX8eiTiGmN-Qc--Y359H6M"

def test_real_jwt_verification():
    """Test verification of real JWT token from frontend"""
    print("🔐 Testing real JWT token verification...")
    print(f"📝 Token issuer: {SUPABASE_URL}/auth/v1")
    print(f"👤 Token subject: 0b3e165c-2661-465f-81ba-cb5e9e4abc61")
    print(f"📧 Token email: doxafotrex55@gmail.com")
    print()

    try:
        # Create Supabase client (same as backend and MT5 server)
        supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase client created successfully")

        # Test token verification using Supabase client (same as backend)
        print("🔍 Verifying JWT token using Supabase client...")
        response = supabase_client.auth.get_user(REAL_JWT_TOKEN)

        if response.user:
            user = response.user
            print("✅ JWT token verified successfully!")
            print(f"🆔 User ID: {user.id}")
            print(f"📧 Email: {user.email}")
            print(f"🔒 Role: {getattr(user, 'role', 'authenticated')}")
            print(f"📅 Created: {getattr(user, 'created_at', 'N/A')}")
            print(f"🔑 Last Sign In: {getattr(user, 'last_sign_in_at', 'N/A')}")

            # Test user extraction (same format as MT5 server auth)
            user_info = {
                'user_id': user.id,
                'email': user.email,
                'role': getattr(user, 'role', 'authenticated'),
                'created_at': getattr(user, 'created_at', None),
                'last_sign_in_at': getattr(user, 'last_sign_in_at', None),
                'email_confirmed_at': getattr(user, 'email_confirmed_at', None),
                'phone': getattr(user, 'phone', None),
                'confirmed_at': getattr(user, 'confirmed_at', None)
            }

            print("\n📋 User info that MT5 server will extract:")
            for key, value in user_info.items():
                print(f"   {key}: {value}")

            return True, user_info
        else:
            print("❌ Token verification failed - no user returned")
            return False, None

    except Exception as e:
        print(f"❌ JWT verification failed: {e}")
        return False, None

if __name__ == "__main__":
    success, user_info = test_real_jwt_verification()
    print(f"\n🎯 Test result: {'PASSED' if success else 'FAILED'}")

    if success:
        print("\n✅ MT5 server can successfully verify JWT tokens from your frontend!")
        print("🔗 Authentication flow: Frontend JWT → Supabase Client → MT5 Server ✅")