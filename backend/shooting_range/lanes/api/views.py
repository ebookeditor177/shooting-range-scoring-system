"""Lane API views."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from shooting_range.lanes.models import Lane, LaneScore
from shooting_range.lanes.api.serializers import LaneSerializer, LaneScoreSerializer


class LaneViewSet(viewsets.ModelViewSet):
    """API endpoint for lanes."""
    
    queryset = Lane.objects.all()
    serializer_class = LaneSerializer
    lookup_field = 'lane_number'
    
    def get_queryset(self):
        queryset = Lane.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by enabled status
        is_enabled = self.request.query_params.get('is_enabled')
        if is_enabled is not None:
            queryset = queryset.filter(is_enabled=is_enabled.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def enable(self, request, lane_number=None):
        """Enable a lane."""
        lane = self.get_object()
        lane.is_enabled = True
        lane.save()
        return Response(LaneSerializer(lane).data)
    
    @action(detail=True, methods=['post'])
    def disable(self, request, lane_number=None):
        """Disable a lane."""
        lane = self.get_object()
        lane.is_enabled = False
        lane.save()
        return Response(LaneSerializer(lane).data)
    
    @action(detail=True, methods=['get'])
    def score(self, request, lane_number=None):
        """Get current score for a lane in active game."""
        lane = self.get_object()
        
        from shooting_range.games.models import Game, GameStatus
        game = Game.objects.filter(
            status=GameStatus.ACTIVE,
            active_lanes=lane
        ).first()
        
        if not game:
            return Response({
                'lane': lane_number,
                'game_id': None,
                'score': 0,
                'hit_count': 0
            })
        
        lane_score = LaneScore.objects.filter(lane=lane, game=game).first()
        if not lane_score:
            return Response({
                'lane': lane_number,
                'game_id': str(game.game_id),
                'score': 0,
                'hit_count': 0
            })
        
        return Response(LaneScoreSerializer(lane_score).data)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get status of all lanes."""
        lanes = Lane.objects.all()
        data = []
        
        for lane in lanes:
            data.append({
                'lane_number': lane.lane_number,
                'name': lane.name,
                'is_enabled': lane.is_enabled,
                'is_active': lane.is_active,
                'is_connected': lane.is_connected,
                'device_id': lane.device.device_id if lane.device else None
            })
        
        return Response(data)
