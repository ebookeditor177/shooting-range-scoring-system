<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'
import { useWebSocket } from '@/composables/useWebSocket'
import TargetSVG from '@/components/TargetSVG.vue'
import ScoreDisplay from '@/components/ScoreDisplay.vue'

const route = useRoute()
const store = useGameStore()

const laneNumber = computed(() => {
  const lane = route.params.lane
  return parseInt(lane as string) || 1
})

// WebSocket connection
const { isConnected, connectionError } = useWebSocket(laneNumber.value)

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
const laneStatus = computed(() => store.lanes.get(laneNumber.value))

const isWinner = computed(() => {
  // In individual mode, anyone who reaches win score wins
  if (store.gameState.winner_lane === null || store.gameState.winner_lane === undefined) {
    // Check if this lane reached the win score
    return store.currentScore(laneNumber.value) >= 1000
  }
  return store.gameState.winner_lane === laneNumber.value
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

// Watch for new hits
watch(() => store.recentHits.length, (newLen, oldLen) => {
  if (newLen > oldLen) {
    playHitSound()
  }
})
</script>

<template>
  <div class="client-screen" :style="{ '--primary-color': store.config.primaryColor }">
    <!-- Header -->
    <header class="header">
      <div class="lane-badge">
        <span class="lane-num">{{ laneNumber }}</span>
      </div>
      <div class="connection-badge" :class="{ connected: isConnected }">
        <span class="conn-dot"></span>
        <span class="conn-text">{{ isConnected ? 'LIVE' : 'OFFLINE' }}</span>
      </div>
    </header>

    <!-- Countdown Overlay -->
    <div v-if="store.isGameCountdown" class="overlay countdown-overlay">
      <div class="countdown-content">
        <div class="countdown-circle">
          <span class="countdown-num">{{ store.countdownValue }}</span>
        </div>
        <div class="countdown-text">GET READY</div>
      </div>
    </div>

    <!-- Active Game -->
    <div v-if="store.isGameActive" class="game-area">
      <!-- Timer -->
      <div class="timer-box">
        <div class="timer-val">{{ store.gameState.remaining_time }}</div>
        <div class="timer-lbl">SECONDS</div>
      </div>

      <!-- Target -->
      <div class="target-area">
        <TargetSVG 
          :primary-color="store.config.primaryColor"
          :hit-effects="store.config.enableVisualEffects"
        />
      </div>

      <!-- Hit Stats -->
      <div class="stats-row">
        <div class="stat-box">
          <div class="stat-val">{{ store.hitsByPosition(laneNumber).head }}</div>
          <div class="stat-lbl">HEAD</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{{ store.hitsByPosition(laneNumber).chest }}</div>
          <div class="stat-lbl">CHEST</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{{ store.hitsByPosition(laneNumber).stomach }}</div>
          <div class="stat-lbl">STOM</div>
        </div>
        <div class="stat-box">
          <div class="stat-val">{{ store.hitsByPosition(laneNumber).left_leg + store.hitsByPosition(laneNumber).right_leg }}</div>
          <div class="stat-lbl">LEGS</div>
        </div>
      </div>
    </div>

    <!-- Score Footer -->
    <footer class="footer">
      <ScoreDisplay 
        :lane-number="laneNumber"
        :target-score="1000"
        :primary-color="store.config.primaryColor"
      />
    </footer>

    <!-- Game End Overlay -->
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

    <!-- Waiting Overlay -->
    <div v-if="!store.isGameActive && !store.isGameCountdown && !store.isGameEnded" class="overlay waiting-overlay">
      <div class="waiting-content">
        <div class="waiting-ring"></div>
        <div class="waiting-title">WAITING FOR GAME</div>
        <div class="waiting-sub">Lane {{ laneNumber }} Ready</div>
      </div>
    </div>

    <!-- Error -->
    <div v-if="connectionError" class="error-banner">
      {{ connectionError }}
    </div>
  </div>
</template>

<style scoped>
/* Base */
.client-screen {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 50%, #0d0d0d 100%);
  position: relative;
  overflow: hidden;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

/* Header */
.header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  z-index: 10;
}

.lane-badge {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 3px solid var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.lane-num {
  font-size: 36px;
  font-weight: 900;
  color: var(--primary-color);
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  border-radius: 30px;
  background: rgba(255, 0, 0, 0.2);
  border: 2px solid rgba(255, 0, 0, 0.5);
}

.connection-badge.connected {
  background: rgba(0, 255, 0, 0.15);
  border-color: rgba(0, 255, 0, 0.5);
}

.conn-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ff3333;
  box-shadow: 0 0 10px #ff3333;
}

.connection-badge.connected .conn-dot {
  background: #00ff66;
  box-shadow: 0 0 10px #00ff66;
}

.conn-text {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #ff3333;
}

.connection-badge.connected .conn-text {
  color: #00ff66;
}

/* Game Area */
.game-area {
  position: absolute;
  top: 110px;
  bottom: 220px;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 20px;
}

/* Timer */
.timer-box {
  background: rgba(0, 0, 0, 0.7);
  border: 2px solid var(--primary-color);
  border-radius: 20px;
  padding: 16px 40px;
  text-align: center;
  box-shadow: 0 0 30px rgba(0, 255, 0, 0.2);
}

.timer-val {
  font-size: 56px;
  font-weight: 900;
  color: var(--primary-color);
  line-height: 1;
  text-shadow: 0 0 20px var(--primary-color);
}

.timer-lbl {
  font-size: 12px;
  letter-spacing: 3px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

/* Target */
.target-area {
  flex: 1;
  width: 100%;
  max-width: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Stats Row */
.stats-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.stat-box {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 12px 20px;
  text-align: center;
  min-width: 70px;
}

.stat-val {
  font-size: 28px;
  font-weight: 800;
  color: var(--primary-color);
}

.stat-lbl {
  font-size: 10px;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

/* Footer */
.footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px 32px 30px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9) 0%, transparent 100%);
}

/* Overlays */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(8px);
}

/* Countdown */
.countdown-overlay {
  background: rgba(0, 0, 0, 0.9);
}

.countdown-content {
  text-align: center;
}

.countdown-circle {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  border: 6px solid var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 60px var(--primary-color), inset 0 0 30px rgba(0, 255, 0, 0.2);
  animation: pulse 1s ease-in-out infinite;
}

.countdown-num {
  font-size: 120px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 40px var(--primary-color);
}

.countdown-text {
  font-size: 32px;
  letter-spacing: 8px;
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
  width: 120px;
  height: 120px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  margin: 0 auto 40px;
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.waiting-title {
  font-size: 28px;
  letter-spacing: 6px;
  color: white;
  font-weight: 300;
}

.waiting-sub {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 12px;
  letter-spacing: 2px;
}

/* Game Over */
.gameover-overlay {
  background: rgba(0, 0, 0, 0.92);
}

.gameover-content {
  text-align: center;
  padding: 40px;
}

.gameover-content.winner {
  animation: winGlow 1.5s ease-in-out infinite;
}

@keyframes winGlow {
  0%, 100% { box-shadow: 0 0 60px var(--primary-color); }
  50% { box-shadow: 0 0 120px var(--primary-color), 0 0 60px var(--primary-color); }
}

.result-badge {
  display: inline-block;
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 6px;
  padding: 12px 40px;
  border-radius: 8px;
  background: var(--primary-color);
  color: #000;
}

.final-score-label {
  font-size: 18px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 30px;
}

.final-score-val {
  font-size: 80px;
  font-weight: 900;
  color: var(--primary-color);
  text-shadow: 0 0 40px var(--primary-color);
}

.breakdown {
  margin-top: 40px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 24px 40px;
  display: inline-block;
}

.break-row {
  display: flex;
  justify-content: space-between;
  gap: 60px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.break-row:last-child {
  border-bottom: none;
}

.break-lbl {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  letter-spacing: 2px;
}

.break-val {
  color: white;
  font-size: 18px;
  font-weight: 700;
}

/* Error */
.error-banner {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 0, 0, 0.8);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 200;
}
</style>
