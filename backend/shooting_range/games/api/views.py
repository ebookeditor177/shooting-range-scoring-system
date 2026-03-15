"""Game API views."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from shooting_range.games.models import Game, GameConfiguration, HitEvent, GameMode, GameStatus
from shooting_range.games.api.serializers import (
    GameSerializer, GameDetailSerializer, GameConfigurationSerializer, HitEventSerializer
)


class GameConfigurationViewSet(viewsets.ModelViewSet):
    """API endpoint for game configurations."""
    
    queryset = GameConfiguration.objects.all()
    serializer_class = GameConfigurationSerializer


class GameViewSet(viewsets.ModelViewSet):
    """API endpoint for games."""
    
    queryset = Game.objects.all()
    lookup_field = 'game_id'
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return GameDetailSerializer
        return GameSerializer
    
    def get_queryset(self):
        queryset = Game.objects.all()
        
        # Filter by status
        game_status = self.request.query_params.get('status')
        if game_status:
            queryset = queryset.filter(status=game_status)
        
        # Filter by mode
        mode = self.request.query_params.get('mode')
        if mode:
            queryset = queryset.filter(mode=mode)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the currently active game."""
        game = Game.objects.filter(
            status__in=[GameStatus.COUNTDOWN, GameStatus.ACTIVE]
        ).first()
        
        if not game:
            return Response({'active': False})
        
        serializer = GameDetailSerializer(game)
        return Response({
            'active': True,
            **serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def start(self, request, game_id=None):
        """Start a game."""
        game = self.get_object()
        
        if game.status != GameStatus.IDLE:
            return Response(
                {'error': f'Cannot start game with status {game.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        game.status = GameStatus.COUNTDOWN
        game.save()
        
        # The actual countdown will be handled by the WebSocket consumer
        return Response(GameSerializer(game).data)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, game_id=None):
        """Stop a game."""
        game = self.get_object()
        
        if game.status != GameStatus.ACTIVE:
            return Response(
                {'error': f'Cannot stop game with status {game.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        game.end()
        
        return Response(GameSerializer(game).data)
    
    @action(detail=True, methods=['post'])
    def reset(self, request, game_id=None):
        """Reset a game."""
        game = self.get_object()
        
        # Delete hit events
        HitEvent.objects.filter(game=game).delete()
        
        # Reset lane scores
        from shooting_range.lanes.models import LaneScore
        LaneScore.objects.filter(game=game).update(score=0, hit_count=0)
        
        # Reset game state
        game.status = GameStatus.IDLE
        game.started_at = None
        game.ended_at = None
        game.save()
        
        return Response(GameSerializer(game).data)
    
    @action(detail=True, methods=['get'])
    def scores(self, request, game_id=None):
        """Get scores for a game."""
        game = self.get_object()
        
        from shooting_range.lanes.api.serializers import LaneScoreSerializer
        scores = game.lane_scores.select_related('lane').all()
        
        return Response(LaneScoreSerializer(scores, many=True).data)
    
    @action(detail=True, methods=['get'])
    def hits(self, request, game_id=None):
        """Get hit events for a game."""
        game = self.get_object()
        
        hits = game.hits.all()
        
        # Filter by lane
        lane = request.query_params.get('lane')
        if lane:
            hits = hits.filter(lane__lane_number=lane)
        
        # Limit results
        limit = request.query_params.get('limit')
        if limit:
            try:
                hits = hits[:int(limit)]
            except ValueError:
                pass
        
        serializer = HitEventSerializer(hits, many=True)
        return Response(serializer.data)


class HitEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for hit events (read-only)."""
    
    queryset = HitEvent.objects.all()
    serializer_class = HitEventSerializer
    
    def get_queryset(self):
        queryset = HitEvent.objects.all()
        
        # Filter by game
        game_id = self.request.query_params.get('game_id')
        if game_id:
            queryset = queryset.filter(game__game_id=game_id)
        
        # Filter by lane
        lane = self.request.query_params.get('lane')
        if lane:
            queryset = queryset.filter(lane__lane_number=lane)
        
        # Filter by position
        position = self.request.query_params.get('position')
        if position:
            queryset = queryset.filter(position=position)
        
        return queryset
