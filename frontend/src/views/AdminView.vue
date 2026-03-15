<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useGameStore, type LaneStatus, type Score } from '@/stores/gameStore'
import { useAdminWebSocket, type WebSocketMessage } from '@/composables/useWebSocket'

const store = useGameStore()

const isConnected = ref(false)
const activeGameId = ref<string | null>(null)

// Game configuration
const gameConfig = ref({
  mode: 'individual' as 'individual' | 'all_lanes',
  duration: 60,
  countdown: 3,
  winScore: 1000,
  useWinScore: false,
  enabledLanes: [1, 2, 3, 4, 5]
})

function handleMessage(msg: WebSocketMessage) {
  console.log('Admin received:', msg)

  switch (msg.type) {
    case 'AUTHENTICATED':
      isConnected.value = true
      // Request status using correct message type
      sendMessage({ type: 'request_status' })
      break

    case 'SYSTEM_STATUS':
      // Update lanes
      if (msg.lanes) {
        store.setAllLanes(msg.lanes)
      }
      // Update active game
      if (msg.active_game) {
        activeGameId.value = msg.active_game.game_id
        store.setGameState({
          game_id: msg.active_game.game_id,
          status: msg.active_game.status,
          mode: msg.active_game.mode
        })
        // Update scores if present
        if (msg.active_game.scores && Array.isArray(msg.active_game.scores)) {
          msg.active_game.scores.forEach((scoreData: { lane: number, score: number, hit_count: number }) => {
            store.scores.set(scoreData.lane, {
              lane: scoreData.lane,
              score: scoreData.score,
              hit_count: scoreData.hit_count
            })
          })
          // Force reactivity
          store.scores = new Map(store.scores)
        }
      }
      break

    case 'LANE_STATUS':
      store.setLaneStatus(msg)
      break

    case 'GAME_STARTED':
    case 'GAME_START':
      store.startGame(msg.game_id, msg.duration)
      activeGameId.value = msg.game_id
      break

    case 'GAME_COUNTDOWN':
      store.setGameState({
        status: 'countdown',
        remaining_time: msg.count
      })
      break

    case 'GAME_STOPPED':
      activeGameId.value = null
      store.resetGame()
      break

    case 'GAME_RESET':
      store.resetGame()
      activeGameId.value = null
      break

    case 'GAME_SCORES':
      // Update scores from active game
      if (msg.scores && Array.isArray(msg.scores)) {
        msg.scores.forEach((scoreData: { lane: number, score: number, hit_count: number }) => {
          store.scores.set(scoreData.lane, {
            lane: scoreData.lane,
            score: scoreData.score,
            hit_count: scoreData.hit_count
          })
        })
        // Force reactivity
        store.scores = new Map(store.scores)
      }
      break

    case 'HIT_EVENT':
      store.addHit({
        lane: msg.lane,
        position: msg.position,
        accuracy: msg.accuracy,
        score: msg.score,
        total_score: msg.total_score,
        hit_count: msg.hit_count,
        timestamp: msg.timestamp
      })
      break

    case 'GAME_END':
      store.endGame(msg.winner_lane, msg.final_scores || [])
      activeGameId.value = null
      break

    case 'ERROR':
      console.error('Server error:', msg.error)
      break
  }
}

function handleConnect() {
  isConnected.value = true
}

function handleDisconnect() {
  isConnected.value = false
}

const { send: sendMessage } = useAdminWebSocket(
  handleMessage,
  handleConnect,
  handleDisconnect
)

function startGame() {
  const lanes = gameConfig.value.enabledLanes
  sendMessage({
    type: 'admin_command',
    command: 'start_game',
    mode: gameConfig.value.mode,
    duration: gameConfig.value.duration,
    countdown: gameConfig.value.countdown,
    win_score: gameConfig.value.winScore,
    use_win_score: gameConfig.value.useWinScore,
    lanes: lanes
  })
}

function stopGame() {
  if (activeGameId.value) {
    sendMessage({
      type: 'admin_command',
      command: 'stop_game',
      game_id: activeGameId.value
    })
  }
}

function resetGame() {
  if (activeGameId.value) {
    sendMessage({
      type: 'admin_command',
      command: 'reset_game',
      game_id: activeGameId.value
    })
  }
}

function toggleLane(laneNumber: number) {
  const index = gameConfig.value.enabledLanes.indexOf(laneNumber)
  if (index > -1) {
    gameConfig.value.enabledLanes.splice(index, 1)
  } else {
    gameConfig.value.enabledLanes.push(laneNumber)
    gameConfig.value.enabledLanes.sort((a, b) => a - b)
  }
}

// Branding configuration
const brandingConfig = ref({
  primaryColor: '#00ff00',
  secondaryColor: '#000000',
  logoUrl: '',
  enableSound: true,
  enableVisualEffects: true
})

function applyBranding() {
  sendMessage({
    type: 'update_config',
    primary_color: brandingConfig.value.primaryColor,
    secondary_color: brandingConfig.value.secondaryColor,
    logo_url: brandingConfig.value.logoUrl,
    enable_sound: brandingConfig.value.enableSound,
    enable_visual_effects: brandingConfig.value.enableVisualEffects
  })
}

function getLaneStatusClass(laneNumber: number) {
  const lane = store.lanes.get(laneNumber)
  if (!lane) return 'unknown'
  if (!lane.is_connected) return 'disconnected'
  if (!lane.is_enabled) return 'disabled'
  return 'connected'
}
</script>

<template>
  <div class="admin-dashboard">
    <header class="admin-header">
      <h1>Shooting Range Admin</h1>
      <div class="connection-indicator" :class="{ connected: isConnected }">
        {{ isConnected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <main class="admin-main">
      <!-- Lane Status Panel -->
      <section class="panel lane-panel">
        <h2>Lane Status</h2>
        <div class="lane-grid">
          <div 
            v-for="lane in 5" 
            :key="lane" 
            class="lane-card"
            :class="getLaneStatusClass(lane)"
          >
            <div class="lane-number">Lane {{ lane }}</div>
            <div class="lane-status">
              <span class="status-badge"></span>
              {{ getLaneStatusClass(lane) }}
            </div>
            <div class="lane-score">
              Score: {{ store.currentScore(lane) }}
            </div>
          </div>
        </div>
      </section>

      <!-- Game Controls -->
      <section class="panel controls-panel">
        <h2>Game Controls</h2>
        
        <div class="control-group">
          <label>Game Mode</label>
          <select v-model="gameConfig.mode">
            <option value="individual">Individual Lane</option>
            <option value="all_lanes">All Lanes</option>
          </select>
        </div>

        <div class="control-row">
          <div class="control-group">
            <label>Duration (seconds)</label>
            <input type="number" v-model="gameConfig.duration" min="10" max="300" />
          </div>
          <div class="control-group">
            <label>Countdown</label>
            <input type="number" v-model="gameConfig.countdown" min="1" max="10" />
          </div>
        </div>

        <div class="control-row">
          <div class="control-group">
            <label>Win Score</label>
            <input type="number" v-model="gameConfig.winScore" min="100" max="10000" />
          </div>
          <div class="control-group checkbox">
            <input type="checkbox" id="useWinScore" v-model="gameConfig.useWinScore" />
            <label for="useWinScore">End on win score</label>
          </div>
        </div>

        <div class="control-group">
          <label>Enabled Lanes</label>
          <div class="lane-toggles">
            <button 
              v-for="lane in 5" 
              :key="lane"
              class="lane-toggle"
              :class="{ active: gameConfig.enabledLanes.includes(lane) }"
              @click="toggleLane(lane)"
            >
              {{ lane }}
            </button>
          </div>
        </div>

        <div class="button-group">
          <button 
            class="btn btn-start" 
            @click="startGame"
            :disabled="activeGameId !== null"
          >
            Start Game
          </button>
          <button 
            class="btn btn-stop" 
            @click="stopGame"
            :disabled="!activeGameId"
          >
            Stop Game
          </button>
          <button 
            class="btn btn-reset" 
            @click="resetGame"
            :disabled="!activeGameId"
          >
            Reset
          </button>
        </div>
      </section>

      <!-- Branding Configuration -->
      <section class="panel branding-panel">
        <h2>Branding & Colors</h2>
        
        <div class="control-row">
          <div class="control-group">
            <label>Primary Color</label>
            <input type="color" v-model="brandingConfig.primaryColor" />
            <span>{{ brandingConfig.primaryColor }}</span>
          </div>
          <div class="control-group">
            <label>Secondary Color</label>
            <input type="color" v-model="brandingConfig.secondaryColor" />
            <span>{{ brandingConfig.secondaryColor }}</span>
          </div>
        </div>

        <div class="control-group">
          <label>Logo URL</label>
          <input type="text" v-model="brandingConfig.logoUrl" placeholder="https://example.com/logo.png" />
        </div>

        <div class="control-row">
          <div class="control-group checkbox">
            <input type="checkbox" id="enableSound" v-model="brandingConfig.enableSound" />
            <label for="enableSound">Enable Sound Effects</label>
          </div>
          <div class="control-group checkbox">
            <input type="checkbox" id="enableVisualEffects" v-model="brandingConfig.enableVisualEffects" />
            <label for="enableVisualEffects">Enable Visual Effects</label>
          </div>
        </div>

        <div class="button-group">
          <button class="btn" @click="applyBranding">
            Apply Branding
          </button>
        </div>
      </section>

      <!-- Live Scoreboard -->
      <section class="panel scoreboard-panel">
        <h2>Live Scoreboard</h2>
        <table class="scoreboard">
          <thead>
            <tr>
              <th>Lane</th>
              <th>Score</th>
              <th>Hits</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="lane in 5" :key="lane">
              <td>Lane {{ lane }}</td>
              <td>{{ store.currentScore(lane) }}</td>
              <td>{{ store.totalHits(lane) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<style scoped>
.admin-dashboard {
  min-height: 100vh;
  background: #1a1a2e;
  color: #fff;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: #16213e;
  border-bottom: 2px solid #0f3460;
}

.admin-header h1 {
  font-size: 24px;
  margin: 0;
}

.connection-indicator {
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(255, 0, 0, 0.3);
  font-size: 14px;
}

.connection-indicator.connected {
  background: rgba(0, 255, 0, 0.3);
}

.admin-main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 20px;
}

.panel {
  background: #16213e;
  border-radius: 12px;
  padding: 20px;
}

.panel h2 {
  font-size: 18px;
  margin: 0 0 20px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid #0f3460;
}

.lane-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 10px;
}

.lane-card {
  background: #0f3460;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  border: 2px solid transparent;
}

.lane-card.connected {
  border-color: #00ff00;
}

.lane-card.disconnected {
  border-color: #ff0000;
}

.lane-card.disabled {
  border-color: #666;
  opacity: 0.5;
}

.lane-number {
  font-weight: bold;
  margin-bottom: 5px;
}

.lane-status {
  font-size: 10px;
  text-transform: uppercase;
  color: #888;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.status-badge {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff0000;
}

.lane-card.connected .status-badge {
  background: #00ff00;
}

.lane-score {
  margin-top: 5px;
  font-size: 14px;
  color: #00ff00;
}

.control-group {
  margin-bottom: 15px;
}

.control-group label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 5px;
}

.control-group input,
.control-group select {
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #0f3460;
  background: #0f3460;
  color: #fff;
  font-size: 14px;
}

.control-group.checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-group.checkbox input {
  width: auto;
}

.control-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.lane-toggles {
  display: flex;
  gap: 10px;
}

.lane-toggle {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: 2px solid #0f3460;
  background: #0f3460;
  color: #fff;
  cursor: pointer;
}

.lane-toggle.active {
  border-color: #00ff00;
  background: rgba(0, 255, 0, 0.2);
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  border: none;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-start {
  background: #00ff00;
  color: #000;
}

.btn-stop {
  background: #ff0000;
  color: #fff;
}

.btn-reset {
  background: #ffa500;
  color: #000;
}

.scoreboard {
  width: 100%;
  border-collapse: collapse;
}

.scoreboard th,
.scoreboard td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #0f3460;
}

.scoreboard th {
  color: #888;
  font-size: 12px;
  text-transform: uppercase;
}

.scoreboard td:last-child {
  text-align: right;
  color: #00ff00;
}

.branding-panel input[type="color"] {
  width: 50px;
  height: 40px;
  border: none;
  cursor: pointer;
}

.branding-panel input[type="text"] {
  width: 100%;
}

.branding-panel span {
  margin-left: 10px;
  font-size: 12px;
  color: #888;
}
</style>
