<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'
import { useClientWebSocket, type WebSocketMessage } from '@/composables/useWebSocket'
import TargetSVG from '@/components/TargetSVG.vue'
import ScoreDisplay from '@/components/ScoreDisplay.vue'

const route = useRoute()
const store = useGameStore()

const laneNumber = computed(() => {
  const lane = route.params.lane
  return parseInt(lane as string) || 1
})

// WebSocket connection
const { isConnected, connectionError } = useClientWebSocket(
  laneNumber.value,
  handleMessage
)

// Timer
let timerInterval: number | null = null

const startTimer = () => {
  if (timerInterval) clearInterval(timerInterval)
  timerInterval = window.setInterval(() => {
    if (store.gameState.remaining_time > 0) {
      store.updateRemainingTime(store.gameState.remaining_time - 1)
    }
  }, 1000)
}

const stopTimer = () => {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// Message handler
function handleMessage(msg: WebSocketMessage) {
  console.log('Received:', msg.type, msg)
  
  switch (msg.type) {
    case 'LANE_STATUS':
      store.setLaneStatus(msg)
      break
      
    case 'GAME_COUNTDOWN':
      store.setCountdown(msg.count)
      break
      
    case 'GAME_START':
      store.startGame(msg.game_id, msg.duration)
      store.setCountdown(0)
      // Update config from game start
      if (msg.config) {
        store.setConfig(msg.config)
      }
      break
      
    case 'GAME_STARTED':
      if (msg.countdown) store.setCountdown(msg.countdown)
      store.startGame(msg.game_id, msg.duration || 60)
      store.setCountdown(0)
      break
      
    case 'GAME_STOP':
      store.setGameState({ status: 'idle' })
      store.setCountdown(0)
      break
      
    case 'GAME_END':
      store.endGame(msg.winner_lane, msg.final_scores || [])
      store.setCountdown(0)
      break
      
    case 'HIT_EVENT':
      if (msg.lane === laneNumber.value) {
        store.addHit(msg as any)
        store.setScore(msg as any)
      }
      break
      
    case 'SCORE_UPDATE':
      store.setScore(msg)
      break
      
    case 'CONFIG_UPDATE':
      store.setConfig(msg)
      break
  }
}

onMounted(() => {
  store.setLaneStatus({ lane_number: laneNumber.value, is_active: false, is_connected: true })
})

onUnmounted(() => {
  stopTimer()
})

watch(() => store.isGameActive, (active) => {
  if (active) {
    store.updateRemainingTime(store.gameState.duration)
    startTimer()
  } else {
    stopTimer()
  }
})

// Computed
const isWinner = computed(() => {
  const winners = store.gameState.winner_lane
  if (Array.isArray(winners)) {
    return winners.includes(laneNumber.value)
  }
  if (winners === null || winners === undefined) {
    return store.currentScore(laneNumber.value) >= (store.config.winScore || 1000)
  }
  return winners === laneNumber.value
})

const isAnyWinner = computed(() => {
  const winners = store.gameState.winner_lane
  if (Array.isArray(winners)) {
    return winners.length > 0
  }
  return winners !== null && winners !== undefined
})

// Hit sound
const playHitSound = () => {
  if (!store.config.enableSound) return
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 800
    osc.type = 'sine'
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.1)
  } catch (e) {}
}

watch(() => store.recentHits.length, (newLen, oldLen) => {
  if (newLen > oldLen) playHitSound()
})
</script>

<template>
  <div class="client-screen" :style="{ '--primary-color': store.config.primaryColor }">
    <!-- Landscape Layout -->
    <div class="landscape-layout">
      
      <!-- LEFT: Target Area -->
      <div class="left-section">
        <div class="target-container">
          <TargetSVG 
            :primary-color="store.config.primaryColor"
            :hit-effects="store.config.enableVisualEffects"
          />
        </div>
        
        <!-- Timer (inside left) -->
        <div v-if="store.isGameActive" class="timer-box">
          <div class="timer-val">{{ store.gameState.remaining_time }}</div>
          <div class="timer-lbl">SEC</div>
        </div>
      </div>
      
      <!-- RIGHT: Stats Area -->
      <div class="right-section">
        <!-- Header -->
        <div class="header">
          <div class="lane-badge">
            <span class="lane-num">{{ laneNumber }}</span>
          </div>
          <div class="connection-badge" :class="{ connected: isConnected }">
            <span class="conn-dot"></span>
            <span class="conn-text">{{ isConnected ? 'LIVE' : 'OFFLINE' }}</span>
          </div>
        </div>
        
        <!-- Score Display -->
        <div class="score-area">
          <div class="score-main">
            <span class="score-label">SCORE</span>
            <span class="score-value">{{ store.currentScore(laneNumber) }}</span>
            <div class="score-target" v-if="store.config.useWinScore">
              Target: {{ store.config.winScore || 1000 }}
            </div>
          </div>
          
          <!-- Progress Bar -->
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ 
                width: `${Math.min((store.currentScore(laneNumber) / (store.config.winScore || 1000)) * 100, 100)}%` 
              }"
            ></div>
          </div>
        </div>
        
        <!-- Hit Stats Grid -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-val">{{ store.hitsByPosition(laneNumber).head }}</div>
            <div class="stat-lbl">HEAD</div>
          </div>
          <div class="stat-card">
            <div class="stat-val">{{ store.hitsByPosition(laneNumber).chest }}</div>
            <div class="stat-lbl">CHEST</div>
          </div>
          <div class="stat-card">
            <div class="stat-val">{{ store.hitsByPosition(laneNumber).stomach }}</div>
            <div class="stat-lbl">STOMACH</div>
          </div>
          <div class="stat-card">
            <div class="stat-val">{{ store.hitsByPosition(laneNumber).left_leg + store.hitsByPosition(laneNumber).right_leg }}</div>
            <div class="stat-lbl">LEGS</div>
          </div>
        </div>
        
        <!-- Total Hits -->
        <div class="total-hits">
          <span>{{ store.totalHits(laneNumber) }} Total Hits</span>
        </div>
      </div>
    </div>
    
    <!-- Overlays -->
    <!-- Countdown -->
    <div v-if="store.isGameCountdown" class="overlay countdown-overlay">
      <div class="countdown-content">
        <div class="countdown-circle">
          <span class="countdown-num">{{ store.countdownValue }}</span>
        </div>
        <div class="countdown-text">GET READY</div>
      </div>
    </div>
    
    <!-- Waiting -->
    <div v-if="!store.isGameActive && !store.isGameCountdown && !store.isGameEnded" class="overlay waiting-overlay">
      <div class="waiting-content">
        <div class="waiting-ring"></div>
        <div class="waiting-title">WAITING FOR GAME</div>
        <div class="waiting-sub">Lane {{ laneNumber }} Ready</div>
      </div>
    </div>
    
    <!-- Game Over -->
    <div v-if="store.isGameEnded" class="overlay gameover-overlay">
      <div class="gameover-content" :class="{ winner: isWinner }">
        <div class="result-badge">{{ isWinner ? 'WINNER' : 'FINISHED' }}</div>
        <div class="final-score-label">FINAL SCORE</div>
        <div class="final-score-val">{{ store.currentScore(laneNumber) }}</div>
        
        <!-- Hit Breakdown -->
        <div class="breakdown">
          <div class="break-row">
            <span class="break-lbl">HEAD</span>
            <span class="break-val">{{ store.hitsByPosition(laneNumber).head }}</span>
          </div>
          <div class="break-row">
            <span class="break-lbl">CHEST</span>
            <span class="break-val">{{ store.hitsByPosition(laneNumber).chest }}</span>
          </div>
          <div class="break-row">
            <span class="break-lbl">STOMACH</span>
            <span class="break-val">{{ store.hitsByPosition(laneNumber).stomach }}</span>
          </div>
          <div class="break-row">
            <span class="break-lbl">LEGS</span>
            <span class="break-val">{{ store.hitsByPosition(laneNumber).left_leg + store.hitsByPosition(laneNumber).right_leg }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Error -->
    <div v-if="connectionError" class="error-banner">{{ connectionError }}</div>
  </div>
</template>

<style scoped>
/* Base */
.client-screen {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%);
  position: relative;
  overflow: hidden;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

/* Landscape Layout */
.landscape-layout {
  display: flex;
  width: 100%;
  height: 100%;
}

/* Left Section - Target */
.left-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

.target-container {
  width: 100%;
  max-width: 400px;
  aspect-ratio: 1/2;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Timer */
.timer-box {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(0, 0, 0, 0.8);
  border: 3px solid var(--primary-color);
  border-radius: 20px;
  padding: 12px 30px;
  text-align: center;
  box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
}

.timer-val {
  font-size: 48px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 20px var(--primary-color);
  line-height: 1;
}

.timer-lbl {
  font-size: 12px;
  letter-spacing: 3px;
  color: rgba(255, 255, 255, 0.5);
}

/* Right Section - Stats */
.right-section {
  width: 380px;
  background: rgba(0, 0, 0, 0.4);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.lane-badge {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.05);
  border: 3px solid var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.2);
}

.lane-num {
  font-size: 32px;
  font-weight: 900;
  color: var(--primary-color);
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(255, 0, 0, 0.2);
  border: 2px solid rgba(255, 0, 0, 0.5);
}

.connection-badge.connected {
  background: rgba(0, 255, 0, 0.15);
  border-color: rgba(0, 255, 0, 0.5);
}

.conn-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff3333;
}

.connection-badge.connected .conn-dot {
  background: #00ff66;
  box-shadow: 0 0 10px #00ff66;
}

.conn-text {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #ff3333;
}

.connection-badge.connected .conn-text {
  color: #00ff66;
}

/* Score Area */
.score-area {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 20px;
  padding: 24px;
  text-align: center;
}

.score-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 4px;
  font-weight: 600;
}

.score-value {
  display: block;
  font-size: 72px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 40px var(--primary-color);
  line-height: 1.1;
  margin: 8px 0;
}

.score-target {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
}

.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 16px;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: 4px;
  transition: width 0.3s ease;
  box-shadow: 0 0 10px var(--primary-color);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 16px;
  text-align: center;
}

.stat-val {
  font-size: 32px;
  font-weight: 800;
  color: var(--primary-color);
}

.stat-lbl {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
  margin-top: 4px;
}

/* Total Hits */
.total-hits {
  text-align: center;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
}

/* Overlays */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(10px);
}

/* Countdown */
.countdown-overlay {
  background: rgba(0, 0, 0, 0.9);
}

.countdown-content {
  text-align: center;
}

.countdown-circle {
  width: 220px;
  height: 220px;
  border-radius: 50%;
  border: 6px solid var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 80px var(--primary-color), inset 0 0 40px rgba(0, 255, 0, 0.15);
  animation: pulse 1s ease-in-out infinite;
}

.countdown-num {
  font-size: 140px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 50px var(--primary-color);
}

.countdown-text {
  font-size: 36px;
  letter-spacing: 10px;
  color: white;
  margin-top: 30px;
  font-weight: 300;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

/* Waiting */
.waiting-overlay {
  background: rgba(0, 0, 0, 0.85);
}

.waiting-content {
  text-align: center;
}

.waiting-ring {
  width: 100px;
  height: 100px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  margin: 0 auto 30px;
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.waiting-title {
  font-size: 24px;
  letter-spacing: 6px;
  color: white;
}

.waiting-sub {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 10px;
}

/* Game Over */
.gameover-overlay {
  background: rgba(0, 0, 0, 0.92);
}

.gameover-content {
  text-align: center;
  padding: 30px;
}

.gameover-content.winner {
  animation: winGlow 2s ease-in-out infinite;
}

@keyframes winGlow {
  0%, 100% { box-shadow: 0 0 60px var(--primary-color); }
  50% { box-shadow: 0 0 120px var(--primary-color); }
}

.result-badge {
  display: inline-block;
  font-size: 20px;
  font-weight: 900;
  letter-spacing: 6px;
  padding: 10px 30px;
  border-radius: 8px;
  background: var(--primary-color);
  color: #000;
}

.final-score-label {
  font-size: 16px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 24px;
}

.final-score-val {
  font-size: 64px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 40px var(--primary-color);
}

.breakdown {
  margin-top: 24px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 16px 24px;
  display: inline-block;
}

.break-row {
  display: flex;
  justify-content: space-between;
  gap: 40px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.break-row:last-child { border-bottom: none; }

.break-lbl {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.break-val {
  color: white;
  font-size: 16px;
  font-weight: 700;
}

/* Error */
.error-banner {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 0, 0, 0.8);
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 12px;
  z-index: 200;
}

/* Portrait fallback */
@media (max-width: 900px) {
  .landscape-layout {
    flex-direction: column;
  }
  
  .left-section {
    flex: 0 0 50%;
  }
  
  .right-section {
    width: 100%;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  .target-container {
    max-width: 250px;
  }
}
</style>
