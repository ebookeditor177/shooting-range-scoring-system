"""Admin configuration for devices."""

from django.contrib import admin
from shooting_range.devices.models import Device, DeviceLog


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'status', 'is_online', 'lane', 'firmware_version', 'last_seen']
    list_filter = ['status', 'is_online']
    search_fields = ['device_id', 'serial_number', 'lane__lane_number']
    ordering = ['device_id']
    
    fieldsets = (
        ('Device Info', {
            'fields': ('device_id', 'serial_number', 'firmware_version')
        }),
        ('Status', {
            'fields': ('status', 'is_online')
        }),
        ('Configuration', {
            'fields': ('supported_sensors',)
        }),
        ('Connection', {
            'fields': ('ip_address', 'channel_name', 'last_seen', 'last_heartbeat')
        }),
        ('Timestamps', {
            'fields': ('registered_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['registered_at', 'updated_at', 'last_seen', 'last_heartbeat']


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'level', 'message', 'timestamp']
    list_filter = ['level', 'timestamp']
    search_fields = ['device__device_id', 'message']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
