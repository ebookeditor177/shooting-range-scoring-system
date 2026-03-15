"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure settings are loaded
django_application = get_asgi_application()

# Import websocket patterns after Django is set up
from shooting_range.websockets.urls import websocket_urlpatterns
from shooting_range.websockets.middleware import JWTAuthMiddleware


application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
