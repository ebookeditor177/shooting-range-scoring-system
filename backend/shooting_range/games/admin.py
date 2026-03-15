"""Admin configuration for games."""

from django.contrib import admin
from shooting_range.games.models import Game, GameConfiguration, HitEvent


@admin.register(GameConfiguration)
class GameConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration', 'countdown_seconds', 'win_score', 'use_win_score', 'updated_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['game_id', 'mode', 'status', 'duration', 'started_at', 'ended_at']
    list_filter = ['status', 'mode']
    search_fields = ['game_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('game_id', 'mode', 'status')
        }),
        ('Configuration', {
            'fields': ('configuration', 'duration', 'countdown_seconds', 'win_score', 'use_win_score')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at')
        }),
        ('Active Lanes', {
            'fields': ('active_lanes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['game_id', 'created_at', 'updated_at']


@admin.register(HitEvent)
class HitEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'game', 'lane', 'position', 'accuracy', 'score', 'event_timestamp']
    list_filter = ['position', 'game']
    search_fields = ['game__game_id', 'lane__lane_number']
    ordering = ['-event_timestamp']
    readonly_fields = ['received_at']
