"""WebSocket URL patterns."""

from django.urls import re_path
from shooting_range.websockets.consumers import DeviceConsumer, ClientConsumer, AdminConsumer

websocket_urlpatterns = [
    # ESP32 device WebSocket connection
    re_path(
        r'ws/device/$',
        DeviceConsumer.as_asgi(),
        name='device-websocket'
    ),
    # Client screen WebSocket connection
    re_path(
        r'ws/client/$',
        ClientConsumer.as_asgi(),
        name='client-websocket'
    ),
    # Admin dashboard WebSocket
    re_path(
        r'ws/admin/$',
        AdminConsumer.as_asgi(),
        name='admin-websocket'
    ),
]
