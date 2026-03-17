"""
WebSocket consumers for device, client, and admin connections.
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseConsumer(AsyncWebsocketConsumer):
    """Base WebSocket consumer with common functionality."""
    
    # Connection groups
    lane_groups: list = []
    device_id: Optional[str] = None
    
    async def connect(self):
        await self.accept()
        logger.info(f"WebSocket connected: {self.scope.get('client', 'unknown')}")
    
    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        await self.leave_all_groups()
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            await self.handle_message(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            await self.send_error(str(e))
    
    async def handle_message(self, data: dict):
        """Process incoming message based on type."""
        message_type = data.get('type')
        if not message_type:
            await self.send_error("Missing message type")
            return
        
        handler = getattr(self, f'handle_{message_type}', None)
        if handler:
            await handler(data)
        else:
            await self.send_error(f"Unknown message type: {message_type}")
    
    async def send_message(self, message: dict):
        """Send a JSON message to the WebSocket."""
        await self.send(text_data=json.dumps(message))
    
    async def send_error(self, error: str, message_type: str = "ERROR"):
        """Send an error message."""
        await self.send_message({
            'type': message_type,
            'error': error,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def join_group(self, group_name: str):
        """Join a channel group."""
        await self.channel_layer.group_add(group_name, self.channel_name)
        if group_name not in self.lane_groups:
            self.lane_groups.append(group_name)
    
    async def leave_group(self, group_name: str):
        """Leave a channel group."""
        await self.channel_layer.group_discard(group_name, self.channel_name)
        if group_name in self.lane_groups:
            self.lane_groups.remove(group_name)
    
    async def leave_all_groups(self):
        """Leave all channel groups."""
        for group_name in self.lane_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
        self.lane_groups = []
    
    async def send_to_group(self, group_name: str, message: dict):
        """Send a message to a specific group."""
        await self.channel_layer.group_send(group_name, message)
    
    # Group message handlers - called when messages are sent via group_send
    async def game_countdown(self, event: dict):
        """Handle game countdown message from group."""
        await self.send_message({
            'type': 'GAME_COUNTDOWN',
            'count': event.get('count'),
            'timestamp': event.get('timestamp')
        })
    
    async def game_start(self, event: dict):
        """Handle game start message from group."""
        await self.send_message({
            'type': 'GAME_START',
            'game_id': event.get('game_id'),
            'duration': event.get('duration'),
            'countdown': event.get('countdown'),
            'timestamp': event.get('timestamp')
        })
    
    async def hit_event(self, event: dict):
        """Handle hit event message from group."""
        await self.send_message({
            'type': 'HIT_EVENT',
            'lane': event.get('lane'),
            'position': event.get('position'),
            'accuracy': event.get('accuracy'),
            'score': event.get('score'),
            'total_score': event.get('total_score'),
            'hit_count': event.get('hit_count'),
            'timestamp': event.get('timestamp')
        })
    
    async def game_end(self, event: dict):
        """Handle game end message from group."""
        await self.send_message({
            'type': 'GAME_END',
            'game_id': event.get('game_id'),
            'winner_lane': event.get('winner_lane'),
            'final_scores': event.get('final_scores', []),
            'timestamp': event.get('timestamp')
        })
    
    async def config_update(self, event: dict):
        """Handle config update message from group."""
        await self.send_message({
            'type': 'CONFIG_UPDATE',
            'primary_color': event.get('primary_color'),
            'secondary_color': event.get('secondary_color'),
            'logo_url': event.get('logo_url'),
            'enable_sound': event.get('enable_sound'),
            'enable_visual_effects': event.get('enable_visual_effects'),
            'timestamp': event.get('timestamp')
        })


class DeviceConsumer(BaseConsumer):
    """
    WebSocket consumer for ESP32 devices.
    
    Handles:
    - Device registration
    - Hit event reception
    - Heartbeat monitoring
    - Device status updates
    """
    
    async def connect(self):
        await super().connect()
        self.device_id = None
        self.heartbeat_task = None
    
    async def disconnect(self, close_code):
        if self.device_id:
            await self.mark_device_offline()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        await super().disconnect(close_code)
    
    async def handle_register_device(self, data: dict):
        """Register an ESP32 device."""
        device_id = data.get('device_id')
        lane_number = data.get('lane')
        sensors = data.get('sensors', [])
        firmware = data.get('firmware', 'unknown')
        
        if not device_id:
            await self.send_error("Missing device_id")
            return
        
        # Create or update device
        device = await self.get_or_create_device(device_id, sensors, firmware)
        
        if lane_number:
            # Associate device with lane
            lane = await self.get_lane_by_number(lane_number)
            if lane:
                await self.assign_device_to_lane(device, lane)
        
        # Join device-specific group
        await self.join_group(f"device_{device_id}")
        
        self.device_id = device_id
        await self.channel_layer.group_add(f"device_{device_id}", self.channel_name)
        
        # Send registration confirmation
        await self.send_message({
            'type': 'REGISTERED',
            'device_id': device_id,
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Start heartbeat monitoring
        self.heartbeat_task = asyncio.create_task(self.heartbeat_monitor())
        
        logger.info(f"Device registered: {device_id} for lane {lane_number}")
    
    async def handle_heartbeat(self, data: dict):
        """Handle device heartbeat."""
        device_id = data.get('device_id')
        if device_id != self.device_id:
            await self.send_error("Device ID mismatch")
            return
        
        await self.update_device_heartbeat()
        
        # Send acknowledgment
        await self.send_message({
            'type': 'HEARTBEAT_ACK',
            'device_id': device_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_hit(self, data: dict):
        """Handle hit event from device."""
        device_id = data.get('device_id')
        
        if device_id != self.device_id:
            await self.send_error("Device ID mismatch")
            return
        
        # Get device and lane
        device = await self.get_device(device_id)
        if not device:
            await self.send_error("Device not registered")
            return
        
        lane = await self.get_device_lane(device)
        if not lane:
            await self.send_error("No lane assigned to device")
            return
        
        # Get position and calculate score
        position = data.get('position', 'unknown')
        accuracy = float(data.get('accuracy', 0.0))
        raw_strength = int(data.get('raw_strength', 0))
        event_timestamp = data.get('event_timestamp')
        
        # Process the hit
        result = await self.process_hit(
            device, lane, position, accuracy, raw_strength, event_timestamp
        )
        
        # Send acknowledgment to device
        await self.send_message({
            'type': 'HIT_ACK',
            'device_id': device_id,
            'score': result.get('score', 0),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        logger.info(f"Hit processed: Lane {lane.lane_number}, {position}, accuracy {accuracy}")
    
    async def heartbeat_monitor(self):
        """Monitor device heartbeat and mark offline if missed."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                device = await self.get_device(self.device_id)
                if device and not device.is_alive:
                    logger.warning(f"Device {self.device_id} heartbeat timeout")
                    await self.mark_device_offline()
                    await self.send_message({
                        'type': 'CONNECTION_LOST',
                        'device_id': self.device_id,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    })
                    break
        except asyncio.CancelledError:
            pass
    
    # Database operations
    @database_sync_to_async
    def get_or_create_device(self, device_id: str, sensors: list, firmware: str):
        from shooting_range.devices.models import Device
        device, created = Device.objects.get_or_create(
            device_id=device_id,
            defaults={
                'supported_sensors': sensors,
                'firmware_version': firmware,
                'status': 'registered',
                'is_online': True
            }
        )
        if not created:
            device.supported_sensors = sensors
            device.firmware_version = firmware
            device.status = 'registered'
            device.is_online = True
            device.save()
        return device
    
    @database_sync_to_async
    def get_lane_by_number(self, lane_number: int):
        from shooting_range.lanes.models import Lane
        lane, created = Lane.objects.select_related('device').get_or_create(
            lane_number=lane_number,
            defaults={'name': f'Lane {lane_number}', 'is_enabled': True}
        )
        return lane
    
    @database_sync_to_async
    def assign_device_to_lane(self, device, lane):
        # Set device on the lane (not lane on device)
        lane.device = device
        lane.save()
    
    @database_sync_to_async
    def get_device(self, device_id: str):
        from shooting_range.devices.models import Device
        try:
            return Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_device_lane(self, device):
        if device.lane:
            return device.lane
        return None
    
    @database_sync_to_async
    def update_device_heartbeat(self):
        from shooting_range.devices.models import Device
        try:
            device = Device.objects.get(device_id=self.device_id)
            device.update_heartbeat()
            return device
        except Device.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_device_offline(self):
        from shooting_range.devices.models import Device
        try:
            device = Device.objects.get(device_id=self.device_id)
            device.mark_offline()
        except Device.DoesNotExist:
            pass
    
    async def process_hit(self, device, lane, position: str, accuracy: float, raw_strength: int, event_timestamp: str):
        from shooting_range.games.models import Game, GameStatus, HitEvent
        from shooting_range.lanes.models import LaneScore as LaneScoreModel
        from asgiref.sync import sync_to_async
        
        # Wrap all DB operations in a sync function
        @sync_to_async
        def process_hit_sync(lane_num, position, accuracy, raw_strength, event_timestamp):
            from django.utils import timezone
            from datetime import datetime
            
            # Find active game for this lane
            game = Game.objects.filter(
                status=GameStatus.ACTIVE,
                active_lanes__lane_number=lane_num
            ).first()
            
            result = {'score': 0, 'game_id': None, 'hit_count': 0, 'total_score': 0}
            
            if not game:
                return result
            
            # Get configuration - use select_related to avoid extra queries
            config = game.configuration
            if not config:
                # Use default sensor points if no configuration
                sensor_points = {
                    'head': 100, 'chest': 50, 'stomach': 30,
                    'left_leg': 20, 'right_leg': 20
                }
            else:
                sensor_points = config.sensor_points or {
                    'head': 100, 'chest': 50, 'stomach': 30,
                    'left_leg': 20, 'right_leg': 20
                }
            
            # Calculate score
            base_points = sensor_points.get(position, 50)
            score = int(base_points * accuracy)
            
            # Get or create lane score
            lane_score, _ = LaneScoreModel.objects.get_or_create(
                game=game,
                lane_id=lane.id,
                defaults={'score': 0, 'hit_count': 0}
            )
            
            # Update score
            lane_score.score += score
            lane_score.hit_count += 1
            lane_score.last_hit_at = timezone.now()
            lane_score.save()
            
            # Create hit event
            try:
                event_time = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
            except:
                event_time = timezone.now()
            
            HitEvent.objects.create(
                game=game,
                lane=lane,
                position=position,
                accuracy=accuracy,
                raw_strength=raw_strength,
                score=score,
                event_timestamp=event_time
            )
            
            # Get hit counts by position from HitEvent table
            from django.db.models import Count
            hits_by_position = dict(
                HitEvent.objects.filter(game=game, lane=lane)
                .values('position')
                .annotate(count=Count('id'))
                .values_list('position', 'count')
            )
            
            result = {
                'score': score,
                'game_id': str(game.game_id),
                'hit_count': lane_score.hit_count,
                'total_score': lane_score.score,
                'hits_by_position': hits_by_position
            }
            
            return result
        
        result = await process_hit_sync(lane.lane_number, position, accuracy, raw_strength, event_timestamp)
        
        # Broadcast hit to all clients (only if there was an active game)
        if result['game_id']:
            hit_message = {
                'type': 'HIT_EVENT',
                'lane': lane.lane_number,
                'position': position,
                'accuracy': accuracy,
                'score': result['score'],
                'total_score': result['total_score'],
                'hit_count': result['hit_count'],
                'hits_by_position': result.get('hits_by_position', {}),
                'timestamp': event_timestamp
            }
            
            # Send to lane group
            await self.channel_layer.group_send(f"lane_{lane.lane_number}", hit_message)
            
            # Send to game group
            await self.channel_layer.group_send(f"game_{result['game_id']}", hit_message)
            
            # Send to game_broadcast group (all connected clients)
            await self.channel_layer.group_send("game_broadcast", hit_message)
        
        # Check if any lane reached win score - end game early if so
        if result['game_id']:
            await self._check_win_score(result['game_id'], lane.lane_number, result['total_score'])
        
        return result
    
    async def _check_win_score(self, game_id: str, lane_number: int, score: int):
        """Check if a lane has reached the win score and end game early."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def check_and_end():
            from shooting_range.games.models import Game, GameStatus
            from shooting_range.lanes.models import Lane, LaneScore
            
            try:
                game = Game.objects.select_related('configuration').get(game_id=game_id, status=GameStatus.ACTIVE)
                
                # Get win score from game config, not settings
                config = game.configuration
                win_score = config.win_score if config else 1000
                use_win_score = game.use_win_score if config else True
                
                # Get all lane scores for this game
                lane_scores = LaneScore.objects.filter(game=game).select_related('lane')
                
                # In individual mode, find ALL lanes that reached win score
                winners = []
                if use_win_score:
                    if game.mode == 'individual':
                        # Individual mode: all lanes that reached win_score are winners
                        for ls in lane_scores:
                            if ls.score >= win_score:
                                winners.append(ls.lane.lane_number)
                        
                        # Mark game as ended if any winner
                        if winners:
                            game.status = GameStatus.ENDED
                            game.ended_at = timezone.now()
                            # Set first winner as primary
                            primary_lane = Lane.objects.filter(lane_number=winners[0]).first()
                            if primary_lane:
                                game.winner_lane = primary_lane
                            game.save()
                            return winners
                    else:
                        # All-lanes mode: first to reach wins
                        if score >= win_score:
                            lane = Lane.objects.filter(lane_number=lane_number).first()
                            if lane:
                                game.winner_lane = lane
                            game.status = GameStatus.ENDED
                            game.ended_at = timezone.now()
                            game.save()
                            return [lane_number]
                return []
            except Game.DoesNotExist:
                return []
        
        winners = await check_and_end()
        
        if winners:
            # Get final scores
            final_scores = await self.get_game_scores_by_id(game_id)
            
            # Broadcast game end
            await self.channel_layer.group_send(f'game_{game_id}', {
                'type': 'GAME_END',
                'winner_lane': winners,  # Now can be a list
                'final_scores': final_scores,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            await self.channel_layer.group_send('all_games', {
                'type': 'GAME_END',
                'winner_lane': winners,
                'final_scores': final_scores,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            await self.channel_layer.group_send('game_broadcast', {
                'type': 'GAME_END',
                'winner_lane': winners,
                'final_scores': final_scores,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
    
    async def get_game_scores(self, game):
        from asgiref.sync import sync_to_async
        scores = []
        
        @sync_to_async
        def get_scores():
            return list(game.lane_scores.select_related('lane').all())
        
        lane_scores = await get_scores()
        for ls in lane_scores:
            scores.append({
                'lane': ls.lane.lane_number,
                'score': ls.score,
                'hit_count': ls.hit_count
            })
        return scores
    
    @database_sync_to_async
    def get_game_scores_by_id(self, game_id: str):
        from shooting_range.games.models import Game
        from shooting_range.hits.models import HitEvent
        from django.db.models import Count
        scores = []
        try:
            game = Game.objects.get(game_id=game_id)
            for ls in game.lane_scores.select_related('lane').all():
                lane_num = ls.lane.lane_number
                hits_by_position = dict(
                    HitEvent.objects.filter(game=game, lane=ls.lane)
                    .values('position')
                    .annotate(count=Count('id'))
                    .values_list('position', 'count')
                )
                scores.append({
                    'lane': lane_num,
                    'score': ls.score,
                    'hit_count': ls.hit_count,
                    'hits_by_position': hits_by_position
                })
        except Game.DoesNotExist:
            pass
        return scores


class ClientConsumer(BaseConsumer):
    """
    WebSocket consumer for client screens.
    
    Handles:
    - Lane subscription
    - Game state updates
    - Real-time hit visualization
    """
    
    async def connect(self):
        await super().connect()
        self.subscribed_lanes: list = []
        self.client_id = f"client_{id(self)}"
        
        # Get lane from query params
        query_string = self.scope.get('query_string', b'').decode()
        from urllib.parse import parse_qs
        query_params = parse_qs(query_string)
        lane_param = query_params.get('lane', [None])[0]
        
        if lane_param:
            try:
                lane_number = int(lane_param)
                group_name = f"lane_{lane_number}"
                await self.join_group(group_name)
                self.subscribed_lanes.append(lane_number)
                
                # Also join all_games for broadcasts
                await self.join_group('all_games')
                
                await self.send_message({
                    'type': 'SUBSCRIBED',
                    'lane': lane_number,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                })
            except ValueError:
                pass
        
        # Also join a general game group (clients will receive game-specific updates)
        await self.join_group('game_broadcast')
        
        # Auto-authenticate for simplicity
        await self.send_message({
            'type': 'AUTHENTICATED',
            'client_id': self.client_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def disconnect(self, close_code):
        await super().disconnect(close_code)
    
    async def handle_authenticate(self, data: dict):
        """Authenticate client with JWT."""
        token = data.get('token')
        client_type = data.get('client_type', 'screen')  # screen, mobile, etc.
        
        # For now, accept simple lane subscription
        # In production, validate JWT token
        self.client_id = data.get('client_id', f"client_{id(self)}")
        
        await self.send_message({
            'type': 'AUTHENTICATED',
            'client_id': self.client_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_subscribe_lane(self, data: dict):
        """Subscribe to a specific lane's updates."""
        lane_number = data.get('lane')
        
        if lane_number is None:
            await self.send_error("Missing lane number")
            return
        
        group_name = f"lane_{lane_number}"
        await self.join_group(group_name)
        self.subscribed_lanes.append(lane_number)
        
        # Also subscribe to all games broadcast
        await self.join_group('all_games')
        
        await self.send_message({
            'type': 'SUBSCRIBED',
            'lane': lane_number,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_subscribe_all_games(self, data: dict):
        """Subscribe to all game broadcasts."""
        await self.join_group('all_games')
        await self.send_message({
            'type': 'SUBSCRIBED',
            'channel': 'all_games',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_unsubscribe_lane(self: object, data: dict) -> None:
        """Unsubscribe from a lane's updates."""
        lane_number = data.get('lane')
        
        if lane_number is None:
            await self.send_error("Missing lane number")
            return
        
        group_name = f"lane_{lane_number}"
        await self.leave_group(group_name)
        self.subscribed_lanes.remove(lane_number)
        
        await self.send_message({
            'type': 'UNSUBSCRIBED',
            'lane': lane_number,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_subscribe_game(self, data: dict):
        """Subscribe to game broadcast updates."""
        game_id = data.get('game_id')
        
        if not game_id:
            await self.send_error("Missing game_id")
            return
        
        group_name = f"game_{game_id}"
        await self.join_group(group_name)
        
        await self.send_message({
            'type': 'SUBSCRIBED',
            'game_id': game_id,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def handle_request_status(self, data: dict):
        """Request current lane/game status."""
        lane_number = data.get('lane')
        
        if lane_number:
            status = await self.get_lane_status(lane_number)
            await self.send_message({
                'type': 'LANE_STATUS',
                'lane': lane_number,
                **status,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        # Also get active game scores if any
        scores = await self.get_active_game_scores()
        if scores:
            await self.send_message({
                'type': 'GAME_SCORES',
                'scores': scores,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
    
    @database_sync_to_async
    def get_active_game_scores(self) -> list:
        """Get scores from the currently active game."""
        from shooting_range.games.models import Game, GameStatus
        from shooting_range.lanes.models import LaneScore
        
        try:
            active_game = Game.objects.filter(status=GameStatus.ACTIVE).first()
            if not active_game:
                return []
            
            lane_scores = LaneScore.objects.filter(
                game=active_game
            ).select_related('lane')
            
            scores = []
            for ls in lane_scores:
                scores.append({
                    'lane': ls.lane.lane_number,
                    'score': ls.score,
                    'hit_count': ls.hit_count
                })
            return scores
        except Exception:
            return []
    
    @database_sync_to_async
    def get_lane_status(self, lane_number: int) -> dict:
        from shooting_range.lanes.models import Lane
        from shooting_range.devices.models import Device
        
        try:
            lane = Lane.objects.select_related('device').get(lane_number=lane_number)
            device = lane.device
            
            return {
                'lane_number': lane.lane_number,
                'name': lane.name or f'Lane {lane.lane_number}',
                'is_active': lane.is_active,
                'is_enabled': lane.is_enabled,
                'enabled_sensors': lane.enabled_sensors,
                'device_connected': device.is_online if device else False,
                'device_id': device.device_id if device else None,
            }
        except Lane.DoesNotExist:
            return {'error': 'Lane not found'}
    
    # Group message handlers
    async def hit_event(self, event: dict):
        """Handle hit event from channel layer."""
        await self.send_message({
            'type': 'HIT_EVENT',
            'lane': event.get('lane'),
            'position': event.get('position'),
            'accuracy': event.get('accuracy'),
            'score': event.get('score'),
            'total_score': event.get('total_score', 0),
            'hit_count': event.get('hit_count', 0),
            'timestamp': event.get('timestamp')
        })
    
    async def game_countdown(self, event: dict):
        """Handle game countdown."""
        await self.send_message({
            'type': 'GAME_COUNTDOWN',
            'count': event.get('count'),
            'lane': event.get('lane'),
            'timestamp': event.get('timestamp')
        })
    
    async def game_start(self, event: dict):
        """Handle game start."""
        await self.send_message({
            'type': 'GAME_START',
            'game_id': event.get('game_id'),
            'duration': event.get('duration'),
            'timestamp': event.get('timestamp')
        })
    
    async def game_stop(self, event: dict):
        """Handle game stop."""
        await self.send_message({
            'type': 'GAME_STOP',
            'game_id': event.get('game_id'),
            'timestamp': event.get('timestamp')
        })
    
    async def game_end(self, event: dict):
        """Handle game end."""
        await self.send_message({
            'type': 'GAME_END',
            'game_id': event.get('game_id'),
            'winner_lane': event.get('winner_lane'),
            'final_scores': event.get('final_scores', []),
            'timestamp': event.get('timestamp')
        })
    
    async def lane_status(self, event: dict):
        """Handle lane status update."""
        await self.send_message({
            'type': 'LANE_STATUS',
            **event,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

    # Also handle uppercase versions (for group_send with uppercase type)
    async def GAME_START(self, event: dict):
        """Handle GAME_START from group."""
        await self.game_start(event)
    
    async def GAME_COUNTDOWN(self, event: dict):
        """Handle GAME_COUNTDOWN from group."""
        await self.game_countdown(event)
    
    async def GAME_END(self, event: dict):
        """Handle GAME_END from group."""
        await self.game_end(event)
    
    async def GAME_STOP(self, event: dict):
        """Handle GAME_STOP from group."""
        await self.game_stop(event)
    
    async def HIT_EVENT(self, event: dict):
        """Handle HIT_EVENT from group."""
        await self.hit_event(event)
    
    async def LANE_STATUS(self, event: dict):
        """Handle LANE_STATUS from group."""
        await self.lane_status(event)


class AdminConsumer(BaseConsumer):
    """
    WebSocket consumer for admin dashboard.
    
    Handles:
    - Game control commands
    - Lane management
    - Configuration updates
    - Live monitoring
    """
    
    async def connect(self):
        await super().connect()
        await self.join_group('admin')
        await self.join_group('all_games')
        await self.join_group('game_broadcast')
        
        # Subscribe to all lane groups for hit events
        for lane_num in range(1, 6):
            await self.join_group(f'lane_{lane_num}')
        
        # Auto-authenticate and send status
        await self.send_message({
            'type': 'AUTHENTICATED',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Send current system status
        await self.send_status()
    
    # Group message handlers for admin dashboard updates
    async def GAME_COUNTDOWN(self, event: dict):
        """Forward countdown to admin."""
        await self.send_message({
            'type': 'GAME_COUNTDOWN',
            'count': event.get('count'),
            'game_id': event.get('game_id'),
            'timestamp': event.get('timestamp')
        })
    
    async def GAME_START(self, event: dict):
        """Forward game start to admin."""
        await self.send_message({
            'type': 'GAME_START',
            'game_id': event.get('game_id'),
            'duration': event.get('duration'),
            'config': event.get('config'),
            'timestamp': event.get('timestamp')
        })
    
    async def HIT_EVENT(self, event: dict):
        """Forward hit event to admin."""
        await self.send_message({
            'type': 'HIT_EVENT',
            'lane': event.get('lane'),
            'position': event.get('position'),
            'accuracy': event.get('accuracy'),
            'score': event.get('score'),
            'total_score': event.get('total_score', 0),
            'hits_by_position': event.get('hits_by_position', {}),
            'timestamp': event.get('timestamp')
        })
    
    async def GAME_END(self, event: dict):
        """Forward game end to admin."""
        await self.send_message({
            'type': 'GAME_END',
            'game_id': event.get('game_id'),
            'winner_lane': event.get('winner_lane'),
            'final_scores': event.get('final_scores', []),
            'timestamp': event.get('timestamp')
        })
    
    async def config_update(self, event: dict):
        """Forward config update to admin."""
        await self.send_message({
            'type': 'CONFIG_UPDATE',
            'primary_color': event.get('primary_color'),
            'secondary_color': event.get('secondary_color'),
            'timestamp': event.get('timestamp')
        })
    
    async def handle_admin_command(self, data: dict):
        """Handle admin commands."""
        command = data.get('command')
        
        if command == 'start_game':
            await self.start_game(data)
        elif command == 'stop_game':
            await self.stop_game(data)
        elif command == 'reset_game':
            await self.reset_game(data)
        elif command == 'get_status':
            await self.send_status()
        else:
            await self.send_error(f"Unknown command: {command}")
    
    async def start_game(self, data: dict):
        """Start a new game."""
        await self._start_game_flow(data)
    
    async def handle_update_config(self, data: dict):
        """Handle configuration update."""
        # Update config (could be saved to database if needed)
        primary_color = data.get('primary_color', '#00ff00')
        secondary_color = data.get('secondary_color', '#000000')
        logo_url = data.get('logo_url', '')
        enable_sound = data.get('enable_sound', True)
        enable_visual_effects = data.get('enable_visual_effects', True)
        
        # Broadcast config update to all clients
        await self.channel_layer.group_send('all_games', {
            'type': 'CONFIG_UPDATE',
            'primary_color': primary_color,
            'secondary_color': secondary_color,
            'logo_url': logo_url,
            'enable_sound': enable_sound,
            'enable_visual_effects': enable_visual_effects,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        
        # Also send to lane groups
        for lane_num in range(1, 6):
            await self.channel_layer.group_send(f'lane_{lane_num}', {
                'type': 'CONFIG_UPDATE',
                'primary_color': primary_color,
                'secondary_color': secondary_color,
                'logo_url': logo_url,
                'enable_sound': enable_sound,
                'enable_visual_effects': enable_visual_effects,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
        
        await self.send_message({
            'type': 'CONFIG_UPDATED',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def stop_game(self, data: dict):
        """Stop the current game."""
        game_id = data.get('game_id')
        
        if game_id:
            await self.end_game(game_id)
            
            await self.send_message({
                'type': 'GAME_STOPPED',
                'game_id': game_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
    
    async def reset_game(self, data: dict):
        """Reset game state."""
        game_id = data.get('game_id')
        
        if game_id:
            await self.reset_game_state(game_id)
            
            await self.send_message({
                'type': 'GAME_RESET',
                'game_id': game_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
    
    async def send_status(self):
        """Send current system status."""
        status = await self.get_system_status()
        await self.send_message({
            'type': 'SYSTEM_STATUS',
            **status,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    @database_sync_to_async
    def get_game_scores_by_id(self, game_id: str):
        from shooting_range.games.models import Game
        scores = []
        try:
            game = Game.objects.get(game_id=game_id)
            for ls in game.lane_scores.select_related('lane').all():
                scores.append({
                    'lane': ls.lane.lane_number,
                    'score': ls.score,
                    'hit_count': ls.hit_count
                })
        except Game.DoesNotExist:
            pass
        return scores
    
    @database_sync_to_async
    def create_game(self, data: dict) -> str:
        import uuid
        from shooting_range.games.models import Game, GameConfiguration, GameMode, GameStatus
        from shooting_range.lanes.models import Lane
        
        game_id = str(uuid.uuid4())
        mode = data.get('mode', GameMode.INDIVIDUAL)
        lanes = data.get('lanes', [])
        
        # Get or create default configuration
        config, _ = GameConfiguration.objects.get_or_create(
            name='default',
            defaults={
                'duration': 60,
                'countdown_seconds': 3,
                'win_score': 1000,
                'sensor_points': {
                    'head': 100,
                    'chest': 50,
                    'stomach': 30,
                    'left_leg': 20,
                    'right_leg': 20,
                }
            }
        )
        
        game = Game.objects.create(
            game_id=game_id,
            mode=mode,
            status=GameStatus.COUNTDOWN,
            configuration=config,
            duration=data.get('duration', config.duration),
            countdown_seconds=data.get('countdown', config.countdown_seconds),
            win_score=data.get('win_score', config.win_score),
            use_win_score=data.get('use_win_score', config.use_win_score)
        )
        
        # Add active lanes
        if lanes:
            active_lanes = Lane.objects.filter(lane_number__in=lanes, is_enabled=True)
            game.active_lanes.set(active_lanes)
        else:
            # All enabled lanes
            game.active_lanes.set(Lane.objects.filter(is_enabled=True))
        
        # Return game_id - countdown will be handled by caller
        return game_id
    
    async def _run_countdown(self, game_id: str, countdown_seconds: int):
        """Run countdown and start game."""
        import asyncio
        from shooting_range.games.models import Game, GameStatus
        from asgiref.sync import sync_to_async
        
        # Get game duration and config
        @sync_to_async
        def get_game_info():
            try:
                game = Game.objects.select_related('configuration').get(game_id=game_id)
                config = game.configuration
                return game.duration, config
            except Game.DoesNotExist:
                return 60, None
        
        game_duration, config = await get_game_info()
        
        # Get config data
        config_data = {}
        if config:
            # Convert sensor_points from JSON string to dict if needed
            sensor_points = config.sensor_points
            if isinstance(sensor_points, str):
                import json
                try:
                    sensor_points = json.loads(sensor_points)
                except:
                    sensor_points = {'head': 100, 'chest': 50, 'stomach': 30, 'left_leg': 20, 'right_leg': 20}
            
            config_data = {
                'primary_color': config.primary_color or '#00ff00',
                'win_score': config.win_score or 1000,
                'use_win_score': config.use_win_score,
                'sensor_points': sensor_points,
            }
        
        for i in range(countdown_seconds, 0, -1):
            # Send to game-specific group
            await self.channel_layer.group_send(f'game_{game_id}', {
                'type': 'GAME_COUNTDOWN',
                'count': i,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            # Also send to all_games group for clients not in specific game group
            await self.channel_layer.group_send('all_games', {
                'type': 'GAME_COUNTDOWN',
                'count': i,
                'game_id': game_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            # Also send to game_broadcast
            await self.channel_layer.group_send('game_broadcast', {
                'type': 'GAME_COUNTDOWN',
                'count': i,
                'game_id': game_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            await asyncio.sleep(1)
        
        # Update game status to active
        @sync_to_async
        def activate_game():
            try:
                game = Game.objects.get(game_id=game_id)
                game.status = GameStatus.ACTIVE
                game.started_at = timezone.now()
                game.save()
            except Game.DoesNotExist:
                pass
        
        await activate_game()
        
        # Send GAME_START to groups (this clears countdown on clients)
        await self.channel_layer.group_send(f'game_{game_id}', {
            'type': 'GAME_START',
            'game_id': game_id,
            'duration': game_duration,
            'config': config_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        await self.channel_layer.group_send('all_games', {
            'type': 'GAME_START',
            'game_id': game_id,
            'duration': game_duration,
            'config': config_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        await self.channel_layer.group_send('game_broadcast', {
            'type': 'GAME_START',
            'game_id': game_id,
            'duration': game_duration,
            'config': config_data,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    async def _start_game_flow(self, data: dict):
        """Start game with countdown."""
        game_id = await self.create_game(data)
        
        if game_id:
            countdown = data.get('countdown', 3)
            duration = data.get('duration', 60)
            
            # Broadcast game start message
            await self.send_message({
                'type': 'GAME_STARTED',
                'game_id': game_id,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
            # Run countdown in background
            import asyncio
            # Use create_task instead of ensure_future for background tasks
            asyncio.create_task(self._run_countdown(game_id, countdown))
            
            # Schedule game end after duration
            asyncio.create_task(self._schedule_game_end(game_id, duration))
            
            # Also start timer broadcast task to keep clients in sync
            asyncio.create_task(self._broadcast_timer(game_id, duration))
    
    async def _broadcast_timer(self, game_id: str, duration: int):
        """Broadcast timer updates every second to keep clients in sync."""
        import asyncio
        
        for remaining in range(duration - 1, -1, -1):
            # Check if game is still active
            from shooting_range.games.models import Game, GameStatus
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def check_active():
                try:
                    game = Game.objects.get(game_id=game_id)
                    return game.status == GameStatus.ACTIVE
                except:
                    return False
            
            is_active = await check_active()
            if not is_active:
                break
            
            # Broadcast timer update
            await self.channel_layer.group_send('game_broadcast', {
                'type': 'TIMER_UPDATE',
                'remaining_time': remaining,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
            await asyncio.sleep(1)
    
    async def _schedule_game_end(self, game_id: str, duration: int):
        """Schedule game to end after duration."""
        import asyncio
        await asyncio.sleep(duration)
        
        # Check if game is still active
        from shooting_range.games.models import Game, GameStatus
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def check_and_end_game():
            try:
                game = Game.objects.select_related('configuration').get(game_id=game_id, status=GameStatus.ACTIVE)
                
                # Get win score from game config, not settings
                config = game.configuration
                win_score = config.win_score if config else 1000
                use_win_score = game.use_win_score if config else True
                
                lane_scores = LaneScore.objects.filter(game=game).select_related('lane')
                
                # Get all winners (lanes with score >= win_score)
                winners = []
                
                if use_win_score:
                    # In individual mode, anyone above win_score wins
                    if game.mode == 'individual':
                        for ls in lane_scores:
                            if ls.score >= win_score:
                                winners.append(ls.lane.lane_number)
                    else:
                        # In all-lanes mode, highest score wins
                        highest = lane_scores.order_by('-score').first()
                        if highest:
                            winners = [highest.lane.lane_number]
                
                # If no one reached win_score in individual mode, highest score still wins
                if not winners and lane_scores:
                    highest = lane_scores.order_by('-score').first()
                    if highest:
                        winners = [highest.lane.lane_number]
                
                game.status = GameStatus.ENDED
                game.ended_at = timezone.now()
                
                # Set winner lane
                if winners:
                    lane = Lane.objects.filter(lane_number=winners[0]).first()
                    if lane:
                        game.winner_lane = lane
                
                game.save()
                
                # Return all winners
                return winners if winners else []
            except Game.DoesNotExist:
                return []
        
        winners = await check_and_end_game()
        
        # Always broadcast GAME_END when timer expires, not just when there are winners
        final_scores = await self.get_game_scores_by_id(game_id)
        
        # Broadcast game end to all groups
        await self.channel_layer.group_send(f'game_{game_id}', {
            'type': 'GAME_END',
            'winner_lane': winners,
            'final_scores': final_scores,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        await self.channel_layer.group_send('all_games', {
            'type': 'GAME_END',
            'winner_lane': winners,
            'final_scores': final_scores,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        await self.channel_layer.group_send('game_broadcast', {
            'type': 'GAME_END',
            'winner_lane': winners,
            'final_scores': final_scores,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    
    @database_sync_to_async
    def end_game(self, game_id: str):
        from shooting_range.games.models import Game, GameStatus
        try:
            game = Game.objects.get(game_id=game_id)
            game.status = GameStatus.ENDED
            game.ended_at = timezone.now()
            game.save()
        except Game.DoesNotExist:
            pass
    
    @database_sync_to_async
    def reset_game_state(self, game_id: str):
        from shooting_range.games.models import Game, HitEvent
        from shooting_range.lanes.models import LaneScore
        try:
            game = Game.objects.get(game_id=game_id)
            # Delete hit events
            HitEvent.objects.filter(game=game).delete()
            # Reset lane scores
            LaneScore.objects.filter(game=game).update(score=0, hit_count=0)
            # Reset game
            game.status = 'idle'
            game.started_at = None
            game.ended_at = None
            game.save()
        except Game.DoesNotExist:
            pass
    
    @database_sync_to_async
    def get_system_status(self) -> dict:
        from shooting_range.lanes.models import Lane
        from shooting_range.devices.models import Device
        from shooting_range.games.models import Game, GameStatus
        
        # Auto-create lanes 1-5 if they don't exist
        for lane_num in range(1, 6):
            Lane.objects.get_or_create(
                lane_number=lane_num,
                defaults={'name': f'Lane {lane_num}', 'is_enabled': True}
            )
        
        lanes = []
        for lane in Lane.objects.all():
            lanes.append({
                'lane_number': lane.lane_number,
                'name': lane.name or f'Lane {lane.lane_number}',
                'is_enabled': lane.is_enabled,
                'is_active': lane.is_active,
                'is_connected': lane.is_connected,
                'device_id': lane.device.device_id if lane.device else None,
                'device_connected': lane.device.is_online if lane.device else False
            })
        
        devices = []
        for device in Device.objects.all():
            devices.append({
                'device_id': device.device_id,
                'is_online': device.is_online,
                'status': device.status,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None
            })
        
        active_game = Game.objects.filter(
            status__in=[GameStatus.COUNTDOWN, GameStatus.ACTIVE]
        ).first()
        
        # Get scores for active game
        active_game_data = None
        if active_game:
            active_game_data = {
                'game_id': str(active_game.game_id),
                'status': active_game.status,
                'mode': active_game.mode
            }
            # Add lane scores
            from shooting_range.lanes.models import LaneScore
            lane_scores = LaneScore.objects.filter(
                game=active_game
            ).select_related('lane')
            scores = []
            for ls in lane_scores:
                scores.append({
                    'lane': ls.lane.lane_number,
                    'score': ls.score,
                    'hit_count': ls.hit_count
                })
            active_game_data['scores'] = scores
        
        return {
            'lanes': lanes,
            'devices': devices,
            'active_game': active_game_data
        }
