"""
Authentication module for MT5 Server
Uses Supabase client authentication (same as backend)
"""

import supabase
from typing import Optional, Dict, Any
import time
import logging

from config import settings

logger = logging.getLogger(__name__)

class SupabaseAuthVerifier:
    """Handles Supabase authentication using client (same as backend)"""

    def __init__(self):
        try:
            self.supabase = supabase.create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
            self.available = True
        except Exception as e:
            logger.warning(f"Supabase client initialization failed: {e}")
            self.supabase = None
            self.available = False

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token using Supabase client (same as backend)"""
        if not self.available:
            logger.warning("Supabase not available, skipping token verification")
            return None

        try:
            # Use Supabase client to verify token (same as backend security.py)
            response = self.supabase.auth.get_user(token)

            if response.user:
                user = response.user
                return {
                    'sub': user.id,
                    'email': user.email,
                    'aud': 'authenticated',
                    'iss': f"{settings.supabase_url}/auth/v1",
                    'role': getattr(user, 'role', 'authenticated'),
                    'exp': int(time.time()) + 3600,  # Mock exp for compatibility
                    'iat': int(time.time())
                }
            else:
                logger.warning("Supabase auth returned no user")
                return None

        except Exception as e:
            logger.error(f"Supabase token verification error: {e}")
            return None

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information using Supabase client"""
        if not self.available:
            logger.warning("Supabase not available, returning mock user")
            return {
                'user_id': 'mock_user',
                'email': 'mock@example.com',
                'role': 'authenticated'
            }

        try:
            response = self.supabase.auth.get_user(token)

            if response.user:
                user = response.user
                return {
                    'user_id': user.id,
                    'email': user.email,
                    'role': getattr(user, 'role', 'authenticated'),
                    'created_at': getattr(user, 'created_at', None),
                    'last_sign_in_at': getattr(user, 'last_sign_in_at', None),
                    'email_confirmed_at': getattr(user, 'email_confirmed_at', None),
                    'phone': getattr(user, 'phone', None),
                    'confirmed_at': getattr(user, 'confirmed_at', None)
                }
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting user from Supabase token: {e}")
            return None

class APIKeyVerifier:
    """Handles API key authentication"""

    def __init__(self, valid_keys: list):
        self.valid_keys = set(valid_keys)

    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key"""
        return api_key in self.valid_keys

class RateLimiter:
    """Simple rate limiter for API requests"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # user_id -> list of timestamps

    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed under rate limit"""
        now = time.time()
        user_requests = self.requests.get(user_id, [])

        # Remove requests older than 1 minute
        user_requests = [t for t in user_requests if now - t < 60]

        if len(user_requests) >= self.requests_per_minute:
            return False

        user_requests.append(now)
        self.requests[user_id] = user_requests
        return True

# Global instances
auth_verifier = SupabaseAuthVerifier()
jwt_verifier = auth_verifier  # For backward compatibility

api_key_verifier = APIKeyVerifier(settings.api_keys.split(',') if settings.api_keys else [])
rate_limiter = RateLimiter(settings.requests_per_minute)

async def get_current_user(token: str) -> Dict[str, Any]:
    """Get current authenticated user from JWT token"""
    user = jwt_verifier.get_user_from_token(token)
    if not user:
        raise ValueError("Invalid or expired token")

    return user

def authenticate_api_key(api_key: str) -> bool:
    """Authenticate using API key"""
    return api_key_verifier.verify_api_key(api_key)

def check_rate_limit(user_id: str) -> bool:
    """Check if user is within rate limits"""
    return rate_limiter.is_allowed(user_id)