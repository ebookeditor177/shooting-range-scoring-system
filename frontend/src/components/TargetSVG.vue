<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import type { HitEvent } from '@/composables/useWebSocket'

const props = defineProps<{
  primaryColor?: string
  hitEffects?: boolean
  laneNumber?: number
}>()

const store = useGameStore()

// Get the lane number - from props or from game state
const currentLane = computed(() => props.laneNumber || store.gameState.game_id as any)

// Human body proportions (realistic silhouette)
// Using standard anatomical proportions: head is ~1/7 to 1/8 of total height
const sensorZones = [
  { id: 'head', cx: 50, cy: 8, r: 7, label: 'HEAD', points: 100 },
  { id: 'chest', cx: 50, cy: 30, r: 12, label: 'CHEST', points: 50 },
  { id: 'stomach', cx: 50, cy: 50, r: 9, label: 'STOMACH', points: 30 },
  { id: 'left_leg', cx: 40, cy: 78, r: 5, label: 'L LEG', points: 20 },
  { id: 'right_leg', cx: 60, cy: 78, r: 5, label: 'R LEG', points: 20 }
]

// Hit markers to display
const hitMarkers = ref<{ position: string; x: number; y: number; id: number; opacity: number }[]>([])
let hitIdCounter = 0

// Flash effect state
const isFlashing = ref(false)

// Track processed hits to avoid duplicates
const processedHitIds = ref<Set<string>>(new Set())

// Add hit marker when a hit event occurs - watch recentHits
watch(() => store.recentHits, (hits) => {
  if (hits && hits.length > 0) {
    // Filter hits for this lane only
    const laneHits = hits.filter(h => h.lane === currentLane.value)
    if (laneHits.length > 0) {
      const latestHit = laneHits[0]
      // Create unique key for this hit
      const hitKey = `${latestHit.timestamp}-${latestHit.position}-${latestHit.lane}`
      if (!processedHitIds.value.has(hitKey)) {
        processedHitIds.value.add(hitKey)
        addHitMarker(latestHit)
        
        // Keep set size manageable
        if (processedHitIds.value.size > 100) {
          const arr = Array.from(processedHitIds.value)
          processedHitIds.value = new Set(arr.slice(-50))
        }
      }
    }
  }
}, { deep: true })

function addHitMarker(hit: HitEvent) {
  const zone = sensorZones.find(z => z.id === hit.position)
  if (!zone) return

  // Add some randomness to hit position within the zone
  const randomOffset = () => (Math.random() - 0.5) * zone.r * 0.7
  const x = zone.cx + randomOffset()
  const y = zone.cy + randomOffset()

  hitMarkers.value.push({
    position: hit.position,
    x,
    y,
    id: hitIdCounter++,
    opacity: 1
  })

  // Trigger flash effect
  if (props.hitEffects !== false) {
    triggerFlash()
  }

  // Remove old hit markers
  if (hitMarkers.value.length > 30) {
    hitMarkers.value = hitMarkers.value.slice(-30)
  }
}

function triggerFlash() {
  isFlashing.value = true
  setTimeout(() => {
    isFlashing.value = false
  }, 150)
}

const primaryColor = computed(() => props.primaryColor || store.config.primaryColor || '#00ff00')
</script>

<template>
  <div class="target-wrapper">
    <div class="target-container" :class="{ 'flash-active': isFlashing }">
      <svg viewBox="0 0 100 120" class="target-svg">
        <!-- Definitions -->
        <defs>
          <linearGradient id="skinGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" :style="`stop-color:${primaryColor};stop-opacity:0.15`" />
            <stop offset="50%" :style="`stop-color:${primaryColor};stop-opacity:0.25`" />
            <stop offset="100%" :style="`stop-color:${primaryColor};stop-opacity:0.15`" />
          </linearGradient>
          <linearGradient id="muscleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" :style="`stop-color:${primaryColor};stop-opacity:0.3`" />
            <stop offset="100%" :style="`stop-color:${primaryColor};stop-opacity:0.1`" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
          <filter id="softGlow">
            <feGaussianBlur stdDeviation="0.5" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        <!-- ========== REALISTIC HUMAN SILHOUETTE ========== -->
        
        <!-- Head - oval shape -->
        <ellipse
          cx="50" cy="8" rx="6" ry="7"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.4"
          filter="url(#softGlow)"
        />
        
        <!-- Neck -->
        <rect x="47" y="14" width="6" height="4" rx="1"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.3"
        />
        
        <!-- Shoulders and torso -->
        <path
          d="M 38 18 
             Q 35 20 34 25 
             L 32 30
             Q 30 35 32 45
             L 35 55
             Q 38 60 40 70
             L 42 85
             L 44 100
             L 48 110
             L 50 115
             L 52 110
             L 56 100
             L 58 85
             L 60 70
             Q 62 60 65 55
             L 68 45
             Q 70 35 68 30
             L 66 25
             Q 65 20 62 18
             Q 55 16 50 16
             Q 45 16 38 18 Z"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.5"
          filter="url(#softGlow)"
        />
        
        <!-- Chest muscle definition -->
        <path
          d="M 38 22 
             Q 40 28 42 35
             Q 50 38 58 35
             Q 60 28 62 22
             Q 55 20 50 20
             Q 45 20 38 22 Z"
          fill="url(#muscleGrad)"
          :stroke="primaryColor"
          stroke-width="0.3"
          opacity="0.6"
        />
        
        <!-- Stomach/abs area -->
        <path
          d="M 40 40
             Q 42 50 44 58
             Q 50 62 56 58
             Q 58 50 60 40
             Q 55 38 50 38
             Q 45 38 40 40 Z"
          fill="url(#muscleGrad)"
          :stroke="primaryColor"
          stroke-width="0.3"
          opacity="0.5"
        />
        
        <!-- Left Arm -->
        <path
          d="M 34 25
             Q 28 28 24 35
             Q 20 42 22 50
             Q 24 55 28 58
             L 32 55
             Q 30 48 30 40
             Q 30 32 34 28
             Z"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.4"
          filter="url(#softGlow)"
        />
        
        <!-- Right Arm -->
        <path
          d="M 66 25
             Q 72 28 76 35
             Q 80 42 78 50
             Q 76 55 72 58
             L 68 55
             Q 70 48 70 40
             Q 70 32 66 28
             Z"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.4"
          filter="url(#softGlow)"
        />
        
        <!-- Left Leg -->
        <path
          d="M 42 70
             Q 38 80 38 90
             Q 38 100 40 108
             Q 42 112 45 110
             L 47 100
             Q 48 90 48 80
             L 48 70
             Z"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.4"
          filter="url(#softGlow)"
        />
        
        <!-- Right Leg -->
        <path
          d="M 52 70
             Q 52 80 52 90
             Q 52 100 55 108
             Q 58 112 60 110
             L 60 100
             Q 62 90 62 80
             Q 62 70 58 70
             Z"
          fill="url(#skinGrad)"
          :stroke="primaryColor"
          stroke-width="0.4"
          filter="url(#softGlow)"
        />

        <!-- ========== SENSOR ZONES (hit targets) ========== -->
        
        <!-- Head zone -->
        <circle cx="50" cy="8" r="5" 
          fill="none" 
          :stroke="primaryColor" 
          stroke-width="0.3" 
          stroke-dasharray="2,2"
          opacity="0.5"
        />
        
        <!-- Chest zone -->
        <ellipse cx="50" cy="28" rx="10" ry="8"
          fill="none"
          :stroke="primaryColor"
          stroke-width="0.3"
          stroke-dasharray="2,2"
          opacity="0.5"
        />
        
        <!-- Stomach zone -->
        <ellipse cx="50" cy="48" rx="8" ry="7"
          fill="none"
          :stroke="primaryColor"
          stroke-width="0.3"
          stroke-dasharray="2,2"
          opacity="0.5"
        />
        
        <!-- Left leg zone -->
        <ellipse cx="42" cy="90" rx="4" ry="12"
          fill="none"
          :stroke="primaryColor"
          stroke-width="0.3"
          stroke-dasharray="2,2"
          opacity="0.5"
        />
        
        <!-- Right leg zone -->
        <ellipse cx="58" cy="90" rx="4" ry="12"
          fill="none"
          :stroke="primaryColor"
          stroke-width="0.3"
          stroke-dasharray="2,2"
          opacity="0.5"
        />

        <!-- ========== HIT MARKERS ========== -->
        <g v-for="marker in hitMarkers" :key="marker.id">
          <!-- Outer glow ring -->
          <circle
            :cx="marker.x"
            :cy="marker.y"
            r="4"
            :fill="primaryColor"
            opacity="0.2"
          />
          <!-- Hit dot -->
          <circle
            :cx="marker.x"
            :cy="marker.y"
            r="2"
            :fill="primaryColor"
            filter="url(#glow)"
          >
            <animate
              attributeName="opacity"
              from="1"
              to="0"
              dur="2s"
              begin="0s"
              fill="freeze"
            />
          </circle>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.target-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.target-container {
  width: 100%;
  max-width: 400px;
  aspect-ratio: 100 / 120;
  transition: background-color 0.1s ease;
}

.target-container.flash-active {
  background-color: rgba(0, 255, 0, 0.1);
}

.target-svg {
  width: 100%;
  height: 100%;
}
</style>
