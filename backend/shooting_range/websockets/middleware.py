"""
JWT Authentication Middleware for WebSocket connections.
"""

import json
import jwt
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser


class JWTAuthMiddleware:
    """
    JWT Authentication Middleware for Channels.
    
    Extracts JWT token from WebSocket query string and validates it.
    For device connections, uses HMAC-based authentication.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        # Check if this is a device connection
        path = scope.get('path', '')
        
        if '/ws/device/' in path:
            # Device authentication using HMAC
            scope['user'] = await self.authenticate_device(query_params)
        else:
            # Client/Admin authentication using JWT
            scope['user'] = await self.authenticate_client(query_params)
        
        return await self.app(scope, receive, send)
    
    async def authenticate_device(self, query_params) -> AnonymousUser:
        """
        Authenticate device using HMAC signature.
        
        Expected query params:
        - device_id: The device identifier
        - timestamp: Unix timestamp (reject if > 5 min old)
        - signature: HMAC-SHA256 signature
        """
        device_id = query_params.get('device_id', [None])[0]
        timestamp = query_params.get('timestamp', [None])[0]
        signature = query_params.get('signature', [None])[0]
        
        if not all([device_id, timestamp, signature]):
            # Allow unauthenticated for development
            return AnonymousUser()
        
        # Check timestamp freshness (5 minutes)
        import time
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                return AnonymousUser()
        except ValueError:
            return AnonymousUser()
        
        # Verify HMAC signature
        import hmac
        import hashlib
        
        message = f"{device_id}:{timestamp}"
        expected_signature = hmac.new(
            settings.HMAC_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return AnonymousUser()
        
        # Mark scope with device info
        return type('DeviceUser', (), {
            'is_authenticated': True,
            'device_id': device_id,
            'is_device': True
        })()
    
    async def authenticate_client(self, query_params) -> AnonymousUser:
        """
        Authenticate client using JWT token.
        
        Expected query params:
        - token: JWT token
        """
        token = query_params.get('token', [None])[0]
        
        if not token:
            # Allow unauthenticated for development
            return AnonymousUser()
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            return type('AuthenticatedUser', (), {
                'is_authenticated': True,
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'is_admin': payload.get('is_admin', False)
            })()
        except jwt.ExpiredSignatureError:
            return AnonymousUser()
        except jwt.InvalidTokenError:
            return AnonymousUser()
