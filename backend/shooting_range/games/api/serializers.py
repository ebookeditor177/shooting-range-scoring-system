"""Game API serializers."""

from rest_framework import serializers
from shooting_range.games.models import Game, GameConfiguration, HitEvent, GameMode, GameStatus


class GameConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for GameConfiguration model."""
    
    class Meta:
        model = GameConfiguration
        fields = [
            'id', 'name', 'description', 'duration', 'countdown_seconds',
            'win_score', 'use_win_score', 'sensor_points', 'use_accuracy_multiplier',
            'enable_sound', 'enable_visual_effects', 'primary_color', 'secondary_color',
            'logo_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class HitEventSerializer(serializers.ModelSerializer):
    """Serializer for HitEvent model."""
    
    lane_number = serializers.IntegerField(source='lane.lane_number', read_only=True)
    
    class Meta:
        model = HitEvent
        fields = [
            'id', 'game', 'lane', 'lane_number', 'position', 'accuracy',
            'raw_strength', 'score', 'event_timestamp', 'received_at'
        ]
        read_only_fields = ['id', 'received_at']


class GameSerializer(serializers.ModelSerializer):
    """Serializer for Game model."""
    
    configuration_name = serializers.CharField(source='configuration.name', read_only=True)
    active_lanes_list = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    
    class Meta:
        model = Game
        fields = [
            'id', 'game_id', 'mode', 'mode_display', 'status', 'status_display',
            'configuration', 'configuration_name', 'duration', 'countdown_seconds',
            'win_score', 'use_win_score', 'active_lanes', 'active_lanes_list',
            'started_at', 'ended_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_active_lanes_list(self, obj):
        return list(obj.active_lanes.values_list('lane_number', flat=True))


class GameDetailSerializer(GameSerializer):
    """Detailed game serializer with scores."""
    
    scores = serializers.SerializerMethodField()
    remaining_time = serializers.IntegerField(read_only=True)
    winner_lane = serializers.SerializerMethodField()
    
    class Meta(GameSerializer.Meta):
        fields = GameSerializer.Meta.fields + ['scores', 'remaining_time', 'winner_lane']
    
    def get_scores(self, obj):
        from shooting_range.lanes.api.serializers import LaneScoreSerializer
        scores = obj.lane_scores.select_related('lane').all()
        return LaneScoreSerializer(scores, many=True).data
    
    def get_winner_lane(self, obj):
        winner = obj.winner_lane
        if winner:
            return {
                'lane_number': winner.lane.lane_number,
                'score': winner.score,
                'hit_count': winner.hit_count
            }
        return None
