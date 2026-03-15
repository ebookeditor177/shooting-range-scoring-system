"""Device API serializers."""

from rest_framework import serializers
from shooting_range.devices.models import Device, DeviceLog


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for Device model."""
    
    lane_number = serializers.IntegerField(source='lane.lane_number', read_only=True, allow_null=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'serial_number', 'firmware_version', 'status',
            'is_online', 'supported_sensors', 'ip_address', 'last_seen',
            'last_heartbeat', 'lane_number', 'registered_at', 'updated_at'
        ]
        read_only_fields = ['id', 'registered_at', 'updated_at']


class DeviceLogSerializer(serializers.ModelSerializer):
    """Serializer for DeviceLog model."""
    
    class Meta:
        model = DeviceLog
        fields = ['id', 'device', 'level', 'message', 'data', 'timestamp']
        read_only_fields = ['id', 'timestamp']
