# Shooting Range API Documentation

## Base URL

```
http://localhost:8000/api/
```

## Authentication

All API endpoints require authentication. Use Django's session authentication or obtain an API token.

## Endpoints

### Lanes

#### List Lanes

```
GET /lanes/
```

Returns a list of all lanes.

**Response:**
```json
[
  {
    "id": 1,
    "lane_number": 1,
    "name": "Lane 1",
    "is_active": true,
    "is_enabled": true,
    "enabled_sensors": ["head", "chest", "stomach"],
    "primary_color": "#00FF00",
    "secondary_color": "#000000",
    "logo_url": "",
    "is_connected": true,
    "device_id": "esp32-001"
  }
]
```

#### Get Lane

```
GET /lanes/{lane_number}/
```

Returns a single lane by lane number.

#### Update Lane

```
PATCH /lanes/{lane_number}/
```

Update lane configuration.

**Request:**
```json
{
  "name": "Lane 1",
  "is_enabled": true,
  "enabled_sensors": ["head", "chest", "stomach"],
  "primary_color": "#00FF00"
}
```

#### Enable Lane

```
POST /lanes/{lane_number}/enable/
```

#### Disable Lane

```
POST /lanes/{lane_number}/disable/
```

#### Get Lane Score

```
GET /lanes/{lane_number}/score/
```

Returns current score for the lane in the active game.

### Games

#### List Games

```
GET /games/
```

Returns a list of all games.

**Query Parameters:**
- `status`: Filter by game status (idle, countdown, active, paused, ended)
- `mode`: Filter by game mode (individual, all_lanes)

#### Get Game

```
GET /games/{game_id}/
```

Returns game details including scores.

#### Get Active Game

```
GET /games/active/
```

Returns the currently active game if any.

#### Start Game

```
POST /games/{game_id}/start/
```

Starts a game that is in idle state.

#### Stop Game

```
POST /games/{game_id}/stop/
```

Stops an active game.

#### Reset Game

```
POST /games/{game_id}/reset/
```

Resets a game, clearing all scores and hit events.

#### Get Game Scores

```
GET /games/{game_id}/scores/
```

Returns scores for all lanes in the game.

#### Get Game Hits

```
GET /games/{game_id}/hits/
```

Returns hit events for the game.

**Query Parameters:**
- `lane`: Filter by lane number
- `limit`: Limit number of results

### Game Configurations

#### List Configurations

```
GET /games/configurations/
```

Returns all game configurations.

#### Create Configuration

```
POST /games/configurations/
```

**Request:**
```json
{
  "name": "Standard Game",
  "description": "Default game configuration",
  "duration": 60,
  "countdown_seconds": 3,
  "win_score": 1000,
  "use_win_score": false,
  "sensor_points": {
    "head": 100,
    "chest": 50,
    "stomach": 30,
    "left_leg": 20,
    "right_leg": 20
  },
  "use_accuracy_multiplier": true,
  "enable_sound": true,
  "enable_visual_effects": true,
  "primary_color": "#00FF00",
  "secondary_color": "#000000"
}
```

#### Get Configuration

```
GET /games/configurations/{id}/
```

#### Update Configuration

```
PATCH /games/configurations/{id}/
```

#### Delete Configuration

```
DELETE /games/configurations/{id}/
```

### Devices

#### List Devices

```
GET /devices/
```

Returns all registered devices.

**Query Parameters:**
- `is_online`: Filter by online status
- `lane`: Filter by lane number

#### Get Device

```
GET /devices/{device_id}/
```

Returns device details.

#### Register Device

```
POST /devices/{device_id}/register/
```

Registers a device.

#### Ping Device

```
POST /devices/{device_id}/ping/
```

Pings a device to check connectivity.

#### Get Device Status

```
GET /devices/status/
```

Returns status of all devices.

### Hit Events

#### List Hit Events

```
GET /devices/hits/
```

Returns hit events.

**Query Parameters:**
- `game_id`: Filter by game
- `lane`: Filter by lane
- `position`: Filter by position (head, chest, stomach, etc.)

## Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

Common status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Server Error

## WebSocket Events

See [WEBSOCKET_PROTOCOL.md](WEBSOCKET_PROTOCOL.md) for WebSocket event documentation.
