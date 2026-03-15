# 1. OBJECTIVE

Build a production-ready, low-latency, multi-lane interactive shooting range scoring system with:
- Django backend (Gunicorn + Django Channels + Redis) for real-time hit event processing
- Vue.js frontend for portrait client screens and admin dashboard
- ESP32 firmware for sensor-based target systems
- Support for 4-5 lanes with <100ms end-to-end latency

The system handles hit events from ESP32 devices, broadcasts real-time updates via WebSockets, manages game modes (Individual Lane Mode and All Lanes Mode), and provides an admin dashboard for configuration.

---

# 2. CONTEXT SUMMARY

**Project Structure:**
- `/workspace/project/backend/` - Django backend (Django 4.x + Channels + DRF)
- Backend already has: Models, API views, WebSocket consumers (skeleton), Settings, Migrations

**Current Implementation Status:**
- ✅ Django models: Game, GameConfiguration, HitEvent, Lane, LaneScore, Device, DeviceLog
- ✅ Game modes: Individual Lane Mode, All Lanes Mode
- ✅ Game lifecycle: Idle, Countdown, Active, Paused, Ended states
- ✅ REST API endpoints for games, devices, configurations
- ✅ WebSocket consumer skeletons (DeviceConsumer, ClientConsumer, AdminConsumer)
- ⚠️ WebSocket routing defined but needs completion

**Key Technologies:**
- Python 3.11+, Django 4.x, Django Channels 4.x
- Redis for pub/sub
- Gunicorn with Uvicorn workers
- Vue.js 3.x (frontend)
- PostgreSQL (production) / SQLite (dev)

**Deliverables Remaining:**
- Vue.js client screens (portrait 1080x1920)
- Vue.js admin dashboard
- WebSocket event handling completion
- Docker Compose setup
- Non-Docker deployment instructions
- API documentation
- Tests
- ESP32 firmware
- Protocol documentation

---

# 2A. DETAILED TECHNICAL SPECIFICATIONS

## Hardware & ESP32 Firmware

### Overview
Each lane has 1 ESP32 controlling 3–5 piezoelectric knock sensors. Minimum sensors: head, chest, stomach. Optional: left_leg, right_leg.

### Hardware Tasks ☐
- [ ] **2A.1** Procure Hardware: ESP32 units, piezo sensors, jumper wires, resistors, power supply
- [ ] **2A.2** Sensor Installation:
  - [ ] Mount sensors on target mannequins
  - [ ] Connect sensors to ESP32 analog pins

### Firmware Tasks ☐
- [ ] **2A.3** Sensor Reading: Sample analog values at high frequency (e.g., 1kHz)
- [ ] **2A.4** Signal Processing: Debounce, low-pass filter to reduce noise
- [ ] **2A.5** Hit Detection: Threshold-based detection, determine hit strength
- [ ] **2A.6** Accuracy Calculation: Normalize signal amplitude (0.0–1.0) based on distance from center
- [ ] **2A.7** Position Mapping: Assign sensor hit to logical position (head/chest/stomach/legs)
- [ ] **2A.8** WebSocket Communication:
  - [ ] Connect to server
  - [ ] Send `register_device` on startup
  - [ ] Send `hit` events in real-time
  - [ ] Send `heartbeat` every 1–2 seconds
- [ ] **2A.9** Error Handling: Reconnect on WiFi drop, fallback to watchdog reset
- [ ] **2A.10** Testing: Validate message structure and timing, simulate multiple hits per second

### ESP32 JSON Message Examples
```json
// Device registration
{
  "type": "register_device",
  "device_id": "esp32-serial-001",
  "lane": 3,
  "sensors": ["head","chest","stomach"],
  "firmware": "v1.0.0",
  "timestamp": "2026-03-15T10:01:23.456Z"
}

// Hit event
{
  "type": "hit",
  "device_id": "esp32-serial-001",
  "lane": 3,
  "position": "head",
  "accuracy": 0.92,
  "raw_strength": 512,
  "event_timestamp": "2026-03-15T10:01:23.789Z"
}

// Heartbeat
{
  "type": "heartbeat",
  "device_id": "esp32-serial-001",
  "timestamp": "2026-03-15T10:01:25.000Z"
}
```

---

## Backend Architecture

### Stack
- Python 3.11+
- Django 4.x
- Django Channels 4.x
- Redis (pub/sub for Channels)
- Gunicorn + Uvicorn worker (ASGI)
- PostgreSQL (production) / SQLite (dev)
- Django REST Framework for admin API

### ASGI / WebSocket Routing
- `/ws/device/` → ESP32 devices connect, send register/hit/heartbeat
- `/ws/client/` → Client screens connect to receive lane/game updates
- Groups:
  - `lane_<n>` → per-lane updates
  - `game_<id>` → broadcast to all clients
- Channel layer: Redis backend for inter-worker communication

### Gunicorn Setup
```bash
gunicorn myproject.asgi:application -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000
```
- 4 workers recommended for 4–5 lanes
- Redis ensures message routing across workers

### Backend Implementation Tasks ☐
- [ ] **2A.11** Django project setup
- [ ] **2A.12** Channels + Redis configuration
- [ ] **2A.13** WebSocket routing (device/client)
- [ ] **2A.14** Authentication: JWT (clients), HMAC (devices)
- [ ] **2A.15** Database models: Lane, Game, HitEvent
- [ ] **2A.16** Admin REST API
- [ ] **2A.17** Event broadcasting logic
- [ ] **2A.18** Logging & error handling

---

## Frontend Requirements

### Client Screens
- Portrait orientation, min 1080×1920
- Top: Lane number, connection status, timer
- Center: Full-body target graphic, hit markers
- Bottom: Score, target score, progress bar
- Countdown & flashing lights + beep before game start
- Hit effects: flash + sound, 300ms animation
- Live score updates via WebSocket
- Configurable branding: colors, logo, hit effects, sounds

### Admin Dashboard
- Lane status panel (green = connected, red = disconnected)
- Game controls: Start, Stop, Reset
- Config: duration, countdown, win score, game mode, enabled lanes, sensors
- Score config: base points per sensor, accuracy multiplier
- Branding: logo, colors, hit effects, sound effects
- Replay/analytics export

### Frontend Tasks ☐
- [ ] **2A.19** Vue project setup
- [ ] **2A.20** Portrait client UI layout
- [ ] **2A.21** Countdown & visual/audio effects
- [ ] **2A.22** Hit animation logic
- [ ] **2A.23** Admin dashboard UI
- [ ] **2A.24** WebSocket client integration
- [ ] **2A.25** Scoreboard live updates

---

## Game Logic & Scoring

### Scoring Rules
- Base points: Head=100, Chest=60, Stomach=40, Legs=20
- Accuracy multiplier: Center=1.0, Near=0.8, Far=0.5

### Game Modes
- Individual lane mode
- All lanes mode

### Game Lifecycle
1. Admin config → 2. Countdown → 3. GAME_START → 4. Real-time hit updates → 5. Score updates → 6. GAME_END

### Game Logic Tasks ☐
- [ ] **2A.26** Implement scoring calculations
- [ ] **2A.27** Implement game modes
- [ ] **2A.28** Implement game lifecycle state machine

---

## Performance & Security Requirements

- End-to-end latency <100ms
- Handle 50+ hits/sec across all lanes
- Secure WebSockets: JWT (client), HMAC (device)
- Validate device_id ↔ lane mapping
- Gunicorn + Redis for concurrency and low-latency

### Performance Tasks ☐
- [ ] **2A.29** Performance testing and optimization
- [ ] **2A.30** Security implementation (JWT/HMAC)

---

## Deployment

- Linux/Windows server
- Services: Django/Gunicorn, Redis, PostgreSQL, Nginx
- Systemd unit files if not using Docker
- Optional Docker Compose deployment
- End-to-end test with hardware and clients

### Deployment Tasks ☐
- [ ] **2A.31** Linux/Windows deployment setup
- [ ] **2A.32** Systemd service configuration
- [ ] **2A.33** Docker Compose setup
- [ ] **2A.34** Nginx configuration
- [ ] **2A.35** End-to-end testing

---

## Deliverables Checklist

- [ ] **2A.36** Django backend (Channels + Gunicorn + Redis)
- [ ] **2A.37** Vue.js frontend (portrait client + admin)
- [ ] **2A.38** ESP32 firmware (PlatformIO/Arduino)
- [ ] **2A.39** Database schema & migrations
- [ ] **2A.40** WebSocket protocol docs
- [ ] **2A.41** API documentation (OpenAPI/Swagger)
- [ ] **2A.42** Docker Compose + non-Docker instructions
- [ ] **2A.43** Unit/integration/firmware tests

---

# 3. APPROACH OVERVIEW

**Implementation Strategy:**
1. **Complete WebSocket Layer** - Finish implementing event handlers for device-client communication
2. **Build Vue.js Frontend** - Create client screens with real-time hit visualization
3. **Build Admin Dashboard** - Create configuration and control panel
4. **Add Tests** - Unit and integration tests for backend
5. **Create ESP32 Firmware** - PlatformIO/Arduino code for sensor devices
6. **Containerize** - Docker Compose for full stack deployment
7. **Document** - API docs and protocol specification

**Rationale:**
- Backend models and API are substantially complete; focus on WebSocket completion and frontend
- Vue.js chosen for reactive real-time updates and existing DRF integration
- WebSocket groups (lane_<n>, game_<id>) enable efficient broadcast to relevant clients
- Gunicorn + Uvicorn workers + Redis ensures scalable, low-latency connections

---

# 4. IMPLEMENTATION STEPS

## Phase 1: Complete Backend WebSocket Layer

### 1.1 Complete WebSocket Event Handlers ☐
- [ ] **1.1.1** Implement ClientConsumer for client screen subscriptions
  - [ ] Join lane groups (lane_<n>) and game groups (game_<id>)
  - [ ] Handle subscribe/unsubscribe messages
  - [ ] Send initial game state on connection
  
- [ ] **1.1.2** Implement hit event broadcasting
  - [ ] Process hits from DeviceConsumer
  - [ ] Broadcast HIT_EVENT to lane_<n> and game_<id> groups
  - [ ] Send SCORE_UPDATE to affected lanes
  
- [ ] **1.1.3** Implement game lifecycle broadcasts
  - [ ] GAME_COUNTDOWN with countdown values (3, 2, 1)
  - [ ] GAME_START with duration
  - [ ] GAME_STOP with final scores
  - [ ] GAME_END with winner information
  
- [ ] **1.1.4** Add LANE_STATUS broadcasts for connection changes

### 1.2 WebSocket Authentication & Security ☐
- [ ] **1.2.1** Implement JWT authentication for client WebSocket connections
- [ ] **1.2.2** Implement HMAC verification for device connections
- [ ] **1.2.3** Add device_id to lane mapping validation
- [ ] **1.2.4** Configure secure WebSocket (WSS) for production

### 1.3 API Documentation ☐
- [ ] **1.3.1** Add drf-spectacular for OpenAPI schema
- [ ] **1.3.2** Generate Swagger UI endpoint
- [ ] **1.3.3** Document WebSocket message protocol

---

## Phase 2: Vue.js Client Screens

### 2.1 Project Setup ☐
- [ ] **2.1.1** Initialize Vue.js 3 project with Vite
- [ ] **2.1.2** Install dependencies (vue-router, pinia, @vueuse/core)
- [ ] **2.1.3** Configure Tailwind CSS for portrait layout
- [ ] **2.1.4** Set up WebSocket client library

### 2.2 Client Screen Components ☐
- [ ] **2.2.1** Create connection status indicator (top bar)
  - [ ] Lane number display
  - [ ] Connection status: red (inactive), green (active)
  
- [ ] **2.2.2** Create full-body target SVG component
  - [ ] Silhouette with sensor zones (head, chest, stomach, legs)
  - [ ] Hit marker overlay
  - [ ] Configurable colors from branding
  
- [ ] **2.2.3** Create score display (bottom bar)
  - [ ] Current score
  - [ ] Target score / win score
  - [ ] Progress bar
  
- [ ] **2.2.4** Implement hit animation effects
  - [ ] Flash effect (~300ms)
  - [ ] Score popup animation
  - [ ] Hit position marker

### 2.3 Client Screen Views ☐
- [ ] **2.3.1** Create LaneView (main game screen)
  - [ ] Connect to WebSocket lane_<n> group
  - [ ] Display target, score, timer
  - [ ] Handle game state transitions
  
- [ ] **2.3.2** Create WaitingView (pre-game)
  - [ ] Connection status
  - [ ] "Waiting for game to start" message
  
- [ ] **2.3.3** Create CountdownView
  - [ ] 3, 2, 1, START display
  - [ ] Audio countdown beeps
  
- [ ] **2.3.4** Create GameOverView
  - [ ] Final score display
  - [ ] Win/lose indicator
  - [ ] Replay button

### 2.4 Real-time Updates ☐
- [ ] **2.4.1** Implement WebSocket connection management
  - [ ] Auto-reconnect logic
  - [ ] Heartbeat ping/pong
  - [ ] Connection state management
  
- [ ] **2.4.2** Handle incoming WebSocket messages
  - [ ] HIT_EVENT: show hit marker + score
  - [ ] SCORE_UPDATE: update score display
  - [ ] GAME_COUNTDOWN: show countdown
  - [ ] GAME_START: transition to game view
  - [ ] GAME_END: show final results

---

## Phase 3: Vue.js Admin Dashboard

### 3.1 Admin Dashboard Components ☐
- [ ] **3.1.1** Create lane status panel
  - [ ] Grid of lanes with status indicators
  - [ ] Green = connected, Red = disconnected
  - [ ] Device info display
  
- [ ] **3.1.2** Create game controls panel
  - [ ] Start/Stop/Reset buttons
  - [ ] Mode selector (Individual/All Lanes)
  - [ ] Lane activation checkboxes
  
- [ ] **3.1.3** Create game configuration form
  - [ ] Duration slider (30s - 300s)
  - [ ] Countdown seconds (3-10)
  - [ ] Win score input
  - [ ] Use win score toggle
  
- [ ] **3.1.4** Create sensor configuration
  - [ ] Enable/disable sensors (head, chest, stomach, legs)
  - [ ] Points per sensor input
  - [ ] Accuracy multiplier toggle
  
- [ ] **3.1.5** Create branding configuration
  - [ ] Primary/secondary color pickers
  - [ ] Logo URL input
  - [ ] Hit effects toggle
  - [ ] Sound effects toggle
  
- [ ] **3.1.6** Create live scoreboard
  - [ ] Real-time score updates
  - [ ] Sort by lane number or score
  - [ ] Highlight winner

### 3.2 Admin Views ☐
- [ ] **3.2.1** Create DashboardView (main admin page)
  - [ ] Lane status + game controls
  - [ ] Quick configuration
  
- [ ] **3.2.2** Create ConfigurationView
  - [ ] Full game config editor
  - [ ] Save/load presets
  
- [ ] **3.2.3** Create AnalyticsView
  - [ ] Hit statistics
  - [ ] Game history
  - [ ] Export functionality

### 3.3 Admin WebSocket Integration ☐
- [ ] **3.3.1** Connect admin to WebSocket admin group
- [ ] **3.3.2** Receive real-time lane status updates
- [ ] **3.3.3** Send game control commands via WebSocket
- [ ] **3.3.4** Receive hit event logs

---

## Phase 4: Testing

### 4.1 Backend Tests ☐
- [ ] **4.1.1** Write unit tests for models
  - [ ] Game scoring calculations
  - [ ] Game status transitions
  - [ ] Lane-device associations
  
- [ ] **4.1.2** Write unit tests for API views
  - [ ] Game CRUD operations
  - [ ] Device registration
  - [ ] Hit event retrieval
  
- [ ] **4.1.3** Write integration tests for WebSocket consumers
  - [ ] Device registration flow
  - [ ] Hit event processing
  - [ ] Game lifecycle broadcasts
  
- [ ] **4.1.4** Create API test client / firmware simulator
  - [ ] Simulate ESP32 device connections
  - [ ] Simulate hit events
  - [ ] Verify broadcast delivery

### 4.2 Frontend Tests ☐
- [ ] **4.2.1** Write component tests with Vitest
- [ ] **4.2.2** Write E2E tests with Playwright
  - [ ] Client screen flows
  -   Admin dashboard flows

---

## Phase 5: ESP32 Firmware

### 5.1 PlatformIO Project Setup ☐
- [ ] **5.1.1** Initialize PlatformIO project
- [ ] **5.1.2** Configure ESP32 board
- [ ] **5.1.3** Add required libraries (WebSocket, ArduinoJSON)

### 5.2 Sensor Implementation ☐
- [ ] **5.2.1** Implement piezo sensor reading
  - [ ] Analog input configuration
  - [ ] Debounce logic (50ms)
  - [ ] Threshold detection
  
- [ ] **5.2.2** Implement position mapping
  - [ ] Map sensors to body positions
  - [ ] Calculate accuracy based on signal strength
  - [ ] Configurable sensor zones

### 5.3 Communication ☐
- [ ] **5.3.1** Implement WebSocket client
  - [ ] Connect to /ws/device/
  - [ ] Handle registration
  - [ ] Send hit events
  
- [ ] **5.3.2** Implement heartbeat
  - [ ] Send heartbeat every 10 seconds
  - [ ] Handle reconnection on disconnect
  
- [ ] **5.3.3** Implement watchdog recovery
  - [ ] Restart on panic
  - [ ] Auto-reconnect logic

### 5.4 Configuration ☐
- [ ] **5.4.1** Add WiFi configuration (SSID/password)
- [ ] **5.4.2** Add server URL configuration
- [ ] **5.4.3** Add lane number configuration

---

## Phase 6: Deployment

### 6.1 Docker Compose ☐
- [ ] **6.1.1** Create Dockerfile for Django backend
- [ ] **6.1.2** Create Dockerfile for Vue.js frontend
- [ ] **6.1.3** Create Dockerfile for Nginx
- [ ] **6.1.4** Create docker-compose.yml
  - [ ] Django/Gunicorn service
  - [ ] Redis service
  - [ ] PostgreSQL service
  - [ ] Vue.js frontend service
  - [   Nginx reverse proxy
  
- [ ] **6.1.5** Configure environment variables
- [ ] **6.1.6** Test full stack startup

### 6.2 Non-Docker Deployment ☐
- [ ] **6.2.1** Create startup scripts
  - [ ] Backend startup (Gunicorn)
  -   Redis startup
  -   Frontend build and serve
  
- [ ] **6.2.2** Create systemd service files
  - [ ] shooting-range-backend.service
  -   shooting-range-frontend.service
  
- [ ] **6.2.3** Create Nginx configuration
- [ ] **6.2.4** Write deployment documentation

---

## Phase 7: Documentation

### 7.1 WebSocket Protocol ☐
- [ ] **7.1.1** Document device messages (register, hit, heartbeat)
- [ ] **7.1.2** Document client messages (subscribe, unsubscribe)
- [ ] **7.1.3** Document server broadcasts (hit_event, score_update, etc.)
- [ ] **7.1.4** Provide JSON examples

### 7.2 API Documentation ☐
- [ ] **7.2.1** Generate OpenAPI spec
- [ ] **7.2.2** Document all REST endpoints
- [ ] **7.2.3** Document authentication requirements

### 7.3 User Documentation ☐
- [ ] **7.3.1** Write admin dashboard guide
- [ ] **7.3.2** Write game setup guide
- [ ] **7.3.3** Write hardware setup guide

---

# 5. TESTING AND VALIDATION

## 5.1 Backend Testing ☐
- [ ] **Unit Tests** - Models, API views, serializers pass with >80% coverage
- [ ] **WebSocket Tests** - Device registration, hit processing, game broadcasts work correctly
- [ ] **Performance Tests** - System handles 50+ hits/sec with <100ms latency

## 5.2 Frontend Testing ☐
- [ ] **Component Tests** - All Vue components render correctly
- [ ] **E2E Tests** - User flows for client screen and admin dashboard work
- [ ] **Visual Tests** - Target SVG, animations, hit markers display correctly

## 5.3 Integration Testing ☐
- [ ] **Full Stack** - End-to-end flow from ESP32 → Backend → Frontend
- [ ] **WebSocket** - Real-time updates reach clients within 100ms
- [ ] **Game Modes** - Individual Lane and All Lanes modes work correctly

## 5.4 Deployment Validation ☐
- [ ] **Docker** - All services start and communicate correctly
- [ ] **Non-Docker** - Services run on Linux/Windows without Docker
- [ ] **Performance** - System meets latency and throughput requirements
