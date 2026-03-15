"""Lane API serializers."""

from rest_framework import serializers
from shooting_range.lanes.models import Lane, LaneScore


class LaneSerializer(serializers.ModelSerializer):
    """Serializer for Lane model."""
    
    is_connected = serializers.BooleanField(read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True, allow_null=True)
    
    class Meta:
        model = Lane
        fields = [
            'id', 'lane_number', 'name', 'is_active', 'is_enabled',
            'enabled_sensors', 'primary_color', 'secondary_color',
            'logo_url', 'is_connected', 'device_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_enabled_sensors(self, value):
        """Validate sensor list against allowed positions."""
        allowed = ['head', 'chest', 'stomach', 'left_leg', 'right_leg']
        for sensor in value:
            if sensor not in allowed:
                raise serializers.ValidationError(f"Invalid sensor: {sensor}")
        return value


class LaneScoreSerializer(serializers.ModelSerializer):
    """Serializer for LaneScore model."""
    
    lane_number = serializers.IntegerField(source='lane.lane_number', read_only=True)
    lane_name = serializers.CharField(source='lane.name', read_only=True)
    
    class Meta:
        model = LaneScore
        fields = ['id', 'lane', 'lane_number', 'lane_name', 'score', 'hit_count', 'last_hit_at']
        read_only_fields = ['id', 'hit_count', 'last_hit_at']
