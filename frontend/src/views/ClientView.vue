<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGameStore } from '@/stores/gameStore'
import { useClientWebSocket, type WebSocketMessage } from '@/composables/useWebSocket'
import TargetSVG from '@/components/TargetSVG.vue'
import ScoreDisplay from '@/components/ScoreDisplay.vue'

const route = useRoute()
const store = useGameStore()

const laneNumber = computed(() => parseInt(route.params.lane as string) || 1)
const isConnected = ref(false)
const connectionError = ref('')

const laneStatus = computed(() => store.lanes.get(laneNumber.value))

function handleMessage(msg: WebSocketMessage) {
  console.log('Received message:', msg)

  switch (msg.type) {
    case 'AUTHENTICATED':
      isConnected.value = true
      sendMessage({
        type: 'subscribe_lane',
        lane: laneNumber.value
      })
      sendMessage({
        type: 'request_status',
        lane: laneNumber.value
      })
      break

    case 'SUBSCRIBED':
      console.log('Subscribed to lane:', msg.lane)
      break

    case 'LANE_STATUS':
      store.setLaneStatus(msg)
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
      if (store.config.enableSound) {
        playHitSound()
      }
      break

    case 'GAME_COUNTDOWN':
      store.setCountdown(msg.count)
      if (store.config.enableSound) {
        playCountdownBeep()
      }
      break

    case 'GAME_START':
      store.startGame(msg.game_id, msg.duration)
      store.setCountdown(0) // Reset countdown
      if (store.config.enableSound) {
        playStartSound()
      }
      break

    case 'GAME_STARTED':
      // Also handle GAME_STARTED for starting the countdown
      if (msg.countdown) {
        store.setCountdown(msg.countdown)
        if (store.config.enableSound) {
          playCountdownBeep()
        }
      }
      store.startGame(msg.game_id, msg.duration || 60)
      store.setCountdown(0) // Reset countdown when game actually starts
      if (store.config.enableSound) {
        playStartSound()
      }
      break

    case 'GAME_STOP':
      store.setGameState({ status: 'idle' })
      store.setCountdown(0) // Reset countdown on stop
      break

    case 'GAME_END':
      store.endGame(msg.winner_lane, msg.final_scores || [])
      store.setCountdown(0) // Reset countdown on end
      if (store.config.enableSound) {
        playEndSound()
      }
      break

    case 'SCORE_UPDATE':
      store.setScore(msg)
      break

    case 'CONFIG_UPDATE':
      store.setConfig({
        primaryColor: msg.primary_color,
        secondaryColor: msg.secondary_color,
        logoUrl: msg.logo_url,
        enableSound: msg.enable_sound,
        enableVisualEffects: msg.enable_visual_effects
      })
      break

    case 'ERROR':
      console.error('Server error:', msg.error)
      break
  }
}

function handleConnect() {
  isConnected.value = true
  connectionError.value = ''
}

function handleDisconnect() {
  isConnected.value = false
  connectionError.value = 'Connection lost. Reconnecting...'
}

const { send: sendMessage } = useClientWebSocket(
  laneNumber.value,
  handleMessage,
  handleConnect,
  handleDisconnect
)

let audioContext: AudioContext | null = null

function initAudio() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  }
}

function playBeep(frequency: number, duration: number) {
  if (!audioContext || !store.config.enableSound) return

  const oscillator = audioContext.createOscillator()
  const gainNode = audioContext.createGain()

  oscillator.connect(gainNode)
  gainNode.connect(audioContext.destination)

  oscillator.frequency.value = frequency
  oscillator.type = 'sine'

  gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration)

  oscillator.start(audioContext.currentTime)
  oscillator.stop(audioContext.currentTime + duration)
}

function playHitSound() {
  playBeep(880, 0.1)
}

function playCountdownBeep() {
  playBeep(440, 0.15)
}

function playStartSound() {
  playBeep(660, 0.3)
}

function playEndSound() {
  playBeep(523, 0.5)
}

let timerInterval: number | null = null

function startTimer() {
  timerInterval = window.setInterval(() => {
    if (store.isGameActive && store.gameState.remaining_time > 0) {
      store.updateRemainingTime(store.gameState.remaining_time - 1)
    }
  }, 1000)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

onMounted(() => {
  initAudio()
  startTimer()
})

onUnmounted(() => {
  stopTimer()
})

watch(() => store.isGameActive, (active) => {
  if (active) {
    store.updateRemainingTime(store.gameState.duration)
  }
})

const isWinner = computed(() => {
  return store.gameState.winner_lane === laneNumber.value
})
</script>

<template>
  <div class="client-screen" :style="{ '--primary-color': store.config.primaryColor }">
    <header class="top-bar">
      <div class="lane-info">
        <span class="lane-number">LANE {{ laneNumber }}</span>
        <span class="lane-name" v-if="laneStatus?.name">{{ laneStatus.name }}</span>
      </div>
      <div class="connection-status" :class="{ connected: isConnected }">
        <span class="status-dot"></span>
        <span class="status-text">{{ isConnected ? 'CONNECTED' : 'DISCONNECTED' }}</span>
      </div>
    </header>

    <main class="main-content">
      <div v-if="store.isGameCountdown" class="countdown-overlay">
        <div class="countdown-number" :style="{ color: store.config.primaryColor }">
          {{ store.countdownValue }}
        </div>
        <div class="countdown-label">GET READY</div>
      </div>

      <div v-if="store.isGameActive" class="game-info">
        <div class="timer-display">
          <span class="timer-value">{{ store.gameState.remaining_time }}</span>
          <span class="timer-label">SEC</span>
        </div>
        
        <div class="hit-stats">
          <div class="stat-item head">
            <span class="stat-icon">🎯</span>
            <span class="stat-count">{{ store.hitsByPosition(laneNumber).head }}</span>
            <span class="stat-label">HEAD</span>
          </div>
          <div class="stat-item chest">
            <span class="stat-icon">💪</span>
            <span class="stat-count">{{ store.hitsByPosition(laneNumber).chest }}</span>
            <span class="stat-label">CHEST</span>
          </div>
          <div class="stat-item stomach">
            <span class="stat-icon">🎯</span>
            <span class="stat-count">{{ store.hitsByPosition(laneNumber).stomach }}</span>
            <span class="stat-label">STOMACH</span>
          </div>
          <div class="stat-item leg">
            <span class="stat-icon">🦵</span>
            <span class="stat-count">{{ store.hitsByPosition(laneNumber).left_leg + store.hitsByPosition(laneNumber).right_leg }}</span>
            <span class="stat-label">LEGS</span>
          </div>
        </div>
      </div>

      <div class="target-wrapper">
        <TargetSVG 
          :primary-color="store.config.primaryColor"
          :hit-effects="store.config.enableVisualEffects"
        />
      </div>
    </main>

    <footer class="bottom-bar">
      <ScoreDisplay 
        :lane-number="laneNumber"
        :target-score="store.gameState.winner_lane ? undefined : 1000"
        :primary-color="store.config.primaryColor"
      />
    </footer>

    <div v-if="connectionError" class="error-toast">
      {{ connectionError }}
    </div>

    <div v-if="store.isGameEnded" class="game-end-overlay">
      <div class="game-end-content">
        <div class="end-glow" :style="{ boxShadow: `0 0 100px ${store.config.primaryColor}` }"></div>
        <div class="end-title" :style="{ color: store.config.primaryColor }">
          {{ isWinner ? '🏆 YOU WIN! 🏆' : store.gameState.winner_lane ? 'GAME OVER' : 'TIME\'S UP!' }}
        </div>
        <div class="final-score">
          <span class="final-label">Final Score</span>
          <span class="final-value" :style="{ color: store.config.primaryColor }">
            {{ store.currentScore(laneNumber) }}
          </span>
        </div>
        <div class="hit-breakdown">
          <div class="breakdown-title">HIT BREAKDOWN</div>
          <div class="breakdown-grid">
            <div class="breakdown-item">
              <span class="breakdown-icon">🎯</span>
              <span class="breakdown-count">{{ store.hitsByPosition(laneNumber).head }}</span>
              <span class="breakdown-label">HEAD</span>
            </div>
            <div class="breakdown-item">
              <span class="breakdown-icon">💪</span>
              <span class="breakdown-count">{{ store.hitsByPosition(laneNumber).chest }}</span>
              <span class="breakdown-label">CHEST</span>
            </div>
            <div class="breakdown-item">
              <span class="breakdown-icon">🎯</span>
              <span class="breakdown-count">{{ store.hitsByPosition(laneNumber).stomach }}</span>
              <span class="breakdown-label">STOMACH</span>
            </div>
            <div class="breakdown-item">
              <span class="breakdown-icon">🦵</span>
              <span class="breakdown-count">{{ store.hitsByPosition(laneNumber).left_leg + store.hitsByPosition(laneNumber).right_leg }}</span>
              <span class="breakdown-label">LEGS</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!store.isGameActive && !store.isGameCountdown && !store.isGameEnded" class="waiting-overlay">
      <div class="waiting-content">
        <div class="waiting-pulse"></div>
        <div class="waiting-title" :style="{ color: store.config.primaryColor }">
          WAITING FOR GAME
        </div>
        <div class="waiting-subtitle">
          Stand by...
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.client-screen {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%);
  position: relative;
  overflow: hidden;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: rgba(0, 0, 0, 0.5);
  z-index: 10;
}

.lane-info {
  display: flex;
  flex-direction: column;
}

.lane-number {
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 3px;
}

.lane-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  background: rgba(255, 0, 0, 0.2);
}

.connection-status.connected {
  background: rgba(0, 255, 0, 0.2);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff0000;
}

.connection-status.connected .status-dot {
  background: #00ff00;
  box-shadow: 0 0 10px #00ff00;
}

.status-text {
  font-size: 12px;
  letter-spacing: 1px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.target-wrapper {
  width: 100%;
  max-width: 500px;
  aspect-ratio: 1 / 2;
}

.timer-display {
  position: absolute;
  top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.timer-value {
  font-size: 48px;
  font-weight: bold;
}

.timer-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.bottom-bar {
  padding: 20px 30px;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
}

.countdown-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  z-index: 100;
}

.countdown-number {
  font-size: 200px;
  font-weight: bold;
  animation: pulse 1s ease-in-out infinite;
  text-shadow: 0 0 50px var(--primary-color);
}

.countdown-label {
  font-size: 24px;
  letter-spacing: 5px;
  margin-top: 20px;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.game-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 20px;
  position: absolute;
  top: 80px;
  left: 0;
  right: 0;
  z-index: 5;
}

.timer-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px 25px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 15px;
  border: 2px solid var(--primary-color);
}

.timer-value {
  font-size: 48px;
  font-weight: bold;
  color: var(--primary-color);
  text-shadow: 0 0 20px var(--primary-color);
}

.timer-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 2px;
}

.hit-stats {
  display: flex;
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 15px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 10px;
  min-width: 60px;
}

.stat-icon {
  font-size: 20px;
}

.stat-count {
  font-size: 24px;
  font-weight: bold;
  color: var(--primary-color);
  text-shadow: 0 0 10px var(--primary-color);
}

.stat-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

.waiting-overlay,
.game-end-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  z-index: 50;
}

.waiting-title,
.end-title {
  font-size: 36px;
  font-weight: bold;
  letter-spacing: 5px;
  text-align: center;
}

.waiting-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 10px;
  text-align: center;
}

.game-end-content {
  text-align: center;
}

.final-score {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.final-label {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.5);
}

.final-value {
  font-size: 72px;
  font-weight: bold;
}

.waiting-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.waiting-pulse {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 3px solid var(--primary-color);
  animation: waitingPulse 2s ease-in-out infinite;
  margin-bottom: 30px;
}

@keyframes waitingPulse {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
    box-shadow: 0 0 20px var(--primary-color);
  }
  50% {
    transform: scale(1);
    opacity: 1;
    box-shadow: 0 0 40px var(--primary-color);
  }
  100% {
    transform: scale(0.8);
    opacity: 0.5;
    box-shadow: 0 0 20px var(--primary-color);
  }
}

.game-end-content {
  text-align: center;
  position: relative;
}

.end-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 300px;
  height: 300px;
  border-radius: 50%;
  opacity: 0.3;
  animation: glowPulse 1s ease-in-out infinite;
}

@keyframes glowPulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.3; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.5; }
}

.end-title {
  font-size: 48px;
  font-weight: bold;
  letter-spacing: 5px;
  text-align: center;
  text-shadow: 0 0 30px var(--primary-color);
  animation: winnerBounce 0.5s ease-out;
}

@keyframes winnerBounce {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

.hit-breakdown {
  margin-top: 40px;
}

.breakdown-title {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 3px;
  margin-bottom: 20px;
}

.breakdown-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.breakdown-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

.breakdown-icon {
  font-size: 24px;
  margin-bottom: 5px;
}

.breakdown-count {
  font-size: 28px;
  font-weight: bold;
  color: var(--primary-color);
  text-shadow: 0 0 10px var(--primary-color);
}

.breakdown-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

.error-toast {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 0, 0, 0.8);
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 14px;
  z-index: 200;
}
</style>
