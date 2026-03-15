"""Device API URLs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shooting_range.devices.api import views

router = DefaultRouter()
router.register(r'logs', views.DeviceLogViewSet, basename='device-log')
router.register(r'', views.DeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
]
