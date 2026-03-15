"""Game API URLs."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shooting_range.games.api import views

router = DefaultRouter()
router.register(r'configurations', views.GameConfigurationViewSet, basename='game-config')
router.register(r'', views.GameViewSet, basename='game')
router.register(r'hits', views.HitEventViewSet, basename='hit')

urlpatterns = [
    path('', include(router.urls)),
]
