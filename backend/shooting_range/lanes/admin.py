"""Admin configuration for lanes."""

from django.contrib import admin
from shooting_range.lanes.models import Lane, LaneScore


@admin.register(Lane)
class LaneAdmin(admin.ModelAdmin):
    list_display = ['lane_number', 'name', 'is_active', 'is_enabled', 'is_connected', 'created_at']
    list_filter = ['is_active', 'is_enabled']
    search_fields = ['name', 'device__device_id']
    ordering = ['lane_number']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('lane_number', 'name', 'is_active', 'is_enabled')
        }),
        ('Target Configuration', {
            'fields': ('enabled_sensors',)
        }),
        ('Hardware', {
            'fields': ('device',)
        }),
        ('Branding', {
            'fields': ('primary_color', 'secondary_color', 'logo_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LaneScore)
class LaneScoreAdmin(admin.ModelAdmin):
    list_display = ['lane', 'game', 'score', 'hit_count', 'updated_at']
    list_filter = ['game']
    search_fields = ['lane__name', 'game__game_id']
