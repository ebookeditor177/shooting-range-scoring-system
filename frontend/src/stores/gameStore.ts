import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { HitEvent } from '@/composables/useWebSocket'

export type GameStatus = 'idle' | 'countdown' | 'active' | 'paused' | 'ended'

export interface LaneStatus {
  lane_number: number
  name: string
  is_enabled: boolean
  is_active: boolean
  is_connected: boolean
  device_id: string | null
}

export interface GameState {
  game_id: string | null
  status: GameStatus
  mode: 'individual' | 'all_lanes'
  duration: number
  remaining_time: number
  winner_lane: number | null
}

export interface Score {
  lane: number
  score: number
  hit_count: number
  hits_by_position?: {
    head: number
    chest: number
    stomach: number
    left_leg: number
    right_leg: number
  }
}

export const useGameStore = defineStore('game', () => {
  // State
  const gameState = ref<GameState>({
    game_id: null,
    status: 'idle',
    mode: 'individual',
    duration: 60,
    remaining_time: 60,
    winner_lane: null
  })

  const lanes = ref<Map<number, LaneStatus>>(new Map())
  const scores = ref<Map<number, Score>>(new Map())
  const recentHits = ref<HitEvent[]>([])
  const countdownValue = ref<number>(0)

  // Config
  const config = ref({
    primaryColor: '#00ff00',
    secondaryColor: '#000000',
    logoUrl: '',
    enableSound: true,
    enableVisualEffects: true,
    winScore: 1000,
    useWinScore: true,
    sensorPoints: {
      head: 100,
      chest: 50,
      stomach: 30,
      left_leg: 20,
      right_leg: 20
    }
  })

  // Getters
  const isGameActive = computed(() => gameState.value.status === 'active')
  const isGameCountdown = computed(() => gameState.value.status === 'countdown')
  const isGameEnded = computed(() => gameState.value.status === 'ended')

  const currentScore = computed(() => (laneNumber: number) => {
    return scores.value.get(laneNumber)?.score ?? 0
  })

  const totalHits = computed(() => (laneNumber: number) => {
    return scores.value.get(laneNumber)?.hit_count ?? 0
  })

  const hitsByPosition = computed(() => (laneNumber: number) => {
    return scores.value.get(laneNumber)?.hits_by_position || {
      head: 0,
      chest: 0,
      stomach: 0,
      left_leg: 0,
      right_leg: 0
    }
  })

  // Actions
  function setLaneStatus(status: LaneStatus) {
    lanes.value.set(status.lane_number, status)
  }

  function setAllLanes(laneList: LaneStatus[]) {
    lanes.value.clear()
    laneList.forEach(lane => lanes.value.set(lane.lane_number, lane))
  }

  function setGameState(state: Partial<GameState>) {
    gameState.value = { ...gameState.value, ...state }
  }

  function setScore(score: Score) {
    scores.value.set(score.lane, score)
  }

  function setAllScores(scoreList: Score[]) {
    scores.value.clear()
    scoreList.forEach(score => scores.value.set(score.lane, score))
  }

  function addHit(hit: HitEvent) {
    recentHits.value.unshift(hit)
    if (recentHits.value.length > 50) {
      recentHits.value.pop()
    }

    // Get existing score or create new
    const existing = scores.value.get(hit.lane) || {
      lane: hit.lane,
      score: 0,
      hit_count: 0,
      hits_by_position: {
        head: 0,
        chest: 0,
        stomach: 0,
        left_leg: 0,
        right_leg: 0
      }
    }

    // Update hit count by position
    const position = hit.position as keyof typeof existing.hits_by_position
    if (existing.hits_by_position && position in existing.hits_by_position) {
      existing.hits_by_position[position]++
    }

    // Update score - create new object to trigger reactivity
    const newScore = {
      lane: hit.lane,
      score: hit.total_score,
      hit_count: hit.hit_count,
      hits_by_position: existing.hits_by_position
    }
    scores.value.set(hit.lane, newScore)
    
    // Force reactivity update
    scores.value = new Map(scores.value)
  }

  function setCountdown(value: number) {
    countdownValue.value = value
    if (value > 0) {
      gameState.value.status = 'countdown'
    }
  }

  function startGame(gameId: string, duration: number) {
    gameState.value.game_id = gameId
    gameState.value.status = 'active'
    gameState.value.duration = duration
    gameState.value.remaining_time = duration
    countdownValue.value = 0
  }

  function endGame(winnerLane: number | number[] | null, finalScores: Score[]) {
    gameState.value.status = 'ended'
    gameState.value.winner_lane = winnerLane
    setAllScores(finalScores)
  }

  function resetGame() {
    gameState.value = {
      game_id: null,
      status: 'idle',
      mode: 'individual',
      duration: 60,
      remaining_time: 60,
      winner_lane: null
    }
    scores.value.clear()
    recentHits.value = []
    countdownValue.value = 0
  }

  function updateRemainingTime(time: number) {
    gameState.value.remaining_time = time
  }

  function setConfig(newConfig: Partial<typeof config.value>) {
    config.value = { ...config.value, ...newConfig }
  }

  return {
    // State
    gameState,
    lanes,
    scores,
    recentHits,
    countdownValue,
    config,
    // Getters
    isGameActive,
    isGameCountdown,
    isGameEnded,
    currentScore,
    totalHits,
    hitsByPosition,
    // Actions
    setLaneStatus,
    setAllLanes,
    setGameState,
    setScore,
    setAllScores,
    addHit,
    setCountdown,
    startGame,
    endGame,
    resetGame,
    updateRemainingTime,
    setConfig
  }
})
