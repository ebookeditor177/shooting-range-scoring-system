# WebSocket Protocol Documentation

## Overview

The Shooting Range system uses WebSockets for real-time communication between:
- **ESP32 Devices**: Send hit events, heartbeats, and receive acknowledgments
- **Client Screens**: Receive game state updates, hit events, and score updates
- **Admin Dashboard**: Send game control commands and receive status updates

## Connection Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/ws/device/` | ESP32 device connections |
| `/ws/client/` | Client screen connections |
| `/ws/admin/` | Admin dashboard connections |

## Authentication

### Device Authentication (HMAC)

Devices authenticate using HMAC-SHA256 signatures in the query string:

```
ws://host/ws/device/?device_id=esp32-001&timestamp=1234567890&signature=abc123...
```

- `device_id`: Unique device identifier
- `timestamp`: Unix timestamp (requests older than 5 minutes are rejected)
- `signature`: HMAC-SHA256 signature of `${device_id}:${timestamp}`

### Client Authentication (JWT)

Clients authenticate using JWT tokens:

```
ws://host/ws/client/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Device Messages

### Server → Device

#### REGISTERED
```json
{
  "type": "REGISTERED",
  "device_id": "esp32-001",
  "status": "ok",
  "timestamp": "2026-03-15T10:01:23.456Z"
}
```

#### HEARTBEAT_ACK
```json
{
  "type": "HEARTBEAT_ACK",
  "device_id": "esp32-001",
  "timestamp": "2026-03-15T10:01:25.000Z"
}
```

#### HIT_ACK
```json
{
  "type": "HIT_ACK",
  "device_id": "esp32-001",
  "score": 95,
  "timestamp": "2026-03-15T10:01:27.000Z"
}
```

#### CONNECTION_LOST
```json
{
  "type": "CONNECTION_LOST",
  "device_id": "esp32-001",
  "timestamp": "2026-03-15T10:01:30.000Z"
}
```

### Device → Server

#### register_device
```json
{
  "type": "register_device",
  "device_id": "esp32-serial-001",
  "lane": 3,
  "sensors": ["head", "chest", "stomach"],
  "firmware": "v1.0.0",
  "timestamp": "2026-03-15T10:01:23.456Z"
}
```

#### hit
```json
{
  "type": "hit",
  "device_id": "esp32-serial-001",
  "lane": 3,
  "position": "head",
  "accuracy": 0.92,
  "raw_strength": 512,
  "event_timestamp": "2026-03-15T10:01:23.789Z"
}
```

#### heartbeat
```json
{
  "type": "heartbeat",
  "device_id": "esp32-serial-001",
  "timestamp": "2026-03-15T10:01:25.000Z"
}
```

## Client Messages

### Server → Client

#### HIT_EVENT
```json
{
  "type": "HIT_EVENT",
  "lane": 2,
  "position": "head",
  "accuracy": 0.95,
  "score": 95,
  "total_score": 285,
  "hit_count": 3,
  "timestamp": "2026-03-15T10:01:23.789Z"
}
```

#### GAME_COUNTDOWN
```json
{
  "type": "GAME_COUNTDOWN",
  "count": 3,
  "lane": 2,
  "timestamp": "2026-03-15T10:01:20.000Z"
}
```

#### GAME_START
```json
{
  "type": "GAME_START",
  "game_id": "abc123-def456",
  "duration": 60,
  "timestamp": "2026-03-15T10:01:23.000Z"
}
```

#### GAME_STOP
```json
{
  "type": "GAME_STOP",
  "game_id": "abc123-def456",
  "timestamp": "2026-03-15T10:02:23.000Z"
}
```

#### GAME_END
```json
{
  "type": "GAME_END",
  "game_id": "abc123-def456",
  "winner_lane": 3,
  "final_scores": [
    { "lane": 1, "score": 450, "hit_count": 8 },
    { "lane": 2, "score": 380, "hit_count": 7 },
    { "lane": 3, "score": 520, "hit_count": 10 }
  ],
  "timestamp": "2026-03-15T10:02:23.000Z"
}
```

#### LANE_STATUS
```json
{
  "type": "LANE_STATUS",
  "lane_number": 2,
  "name": "Lane 2",
  "is_active": true,
  "is_enabled": true,
  "enabled_sensors": ["head", "chest", "stomach"],
  "device_connected": true,
  "device_id": "esp32-002",
  "timestamp": "2026-03-15T10:01:00.000Z"
}
```

### Client → Server

#### subscribe_lane
```json
{
  "type": "subscribe_lane",
  "lane": 2
}
```

#### unsubscribe_lane
```json
{
  "type": "unsubscribe_lane",
  "lane": 2
}
```

#### subscribe_game
```json
{
  "type": "subscribe_game",
  "game_id": "abc123-def456"
}
```

#### request_status
```json
{
  "type": "request_status",
  "lane": 2
}
```

## Admin Messages

### Admin → Server

#### admin_command

Start game:
```json
{
  "type": "admin_command",
  "command": "start_game",
  "mode": "individual",
  "duration": 60,
  "countdown": 3,
  "win_score": 1000,
  "use_win_score": false,
  "lanes": [1, 2, 3]
}
```

Stop game:
```json
{
  "type": "admin_command",
  "command": "stop_game",
  "game_id": "abc123-def456"
}
```

Reset game:
```json
{
  "type": "admin_command",
  "command": "reset_game",
  "game_id": "abc123-def456"
}
```

Get status:
```json
{
  "type": "admin_command",
  "command": "get_status"
}
```

### Server → Admin

#### SYSTEM_STATUS
```json
{
  "type": "SYSTEM_STATUS",
  "lanes": [
    {
      "lane_number": 1,
      "name": "Lane 1",
      "is_enabled": true,
      "is_active": true,
      "is_connected": true,
      "device_id": "esp32-001"
    }
  ],
  "devices": [
    {
      "device_id": "esp32-001",
      "is_online": true,
      "status": "online",
      "last_seen": "2026-03-15T10:01:00.000Z"
    }
  ],
  "active_game": {
    "game_id": "abc123-def456",
    "status": "active",
    "mode": "individual"
  },
  "timestamp": "2026-03-15T10:01:00.000Z"
}
```

## Groups

The server uses channel groups for broadcasting:

- `lane_<n>` - All clients subscribed to lane n
- `game_<id>` - All clients in game id
- `device_<id>` - Device-specific messages
- `admin` - All admin dashboard clients

## Heartbeat Protocol

Devices must send heartbeats every 5 seconds. If no heartbeat is received for 30 seconds, the device is marked as offline.

## Error Handling

All errors are returned in the format:
```json
{
  "type": "ERROR",
  "error": "Error message description",
  "timestamp": "2026-03-15T10:01:00.000Z"
}
```
