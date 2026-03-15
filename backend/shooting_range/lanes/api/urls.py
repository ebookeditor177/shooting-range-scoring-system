"""Lane API URLs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shooting_range.lanes.api import views

router = DefaultRouter()
router.register(r'', views.LaneViewSet, basename='lane')

urlpatterns = [
    path('', include(router.urls)),
]
