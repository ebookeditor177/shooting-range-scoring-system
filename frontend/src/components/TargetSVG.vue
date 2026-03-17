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

// Sensor positions on the target silhouette (percentage-based)
const sensorZones = [
  { id: 'head', cx: 50, cy: 10, r: 10, label: 'HEAD', points: 100 },
  { id: 'chest', cx: 50, cy: 32, r: 14, label: 'CHEST', points: 50 },
  { id: 'stomach', cx: 50, cy: 52, r: 10, label: 'STOMACH', points: 30 },
  { id: 'left_leg', cx: 38, cy: 78, r: 6, label: 'L LEG', points: 20 },
  { id: 'right_leg', cx: 62, cy: 78, r: 6, label: 'R LEG', points: 20 }
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
  const randomOffset = () => (Math.random() - 0.5) * zone.r * 0.6
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
  <div class="target-container" :class="{ 'flash-active': isFlashing }">
    <svg viewBox="0 0 100 100" class="target-svg">
      <!-- Definitions -->
      <defs>
        <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" :style="`stop-color:${primaryColor};stop-opacity:0.3`" />
          <stop offset="50%" :style="`stop-color:${primaryColor};stop-opacity:0.15`" />
          <stop offset="100%" :style="`stop-color:${primaryColor};stop-opacity:0.05`" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <filter id="shadow">
          <feDropShadow dx="0" dy="0" stdDeviation="2" :flood-color="primaryColor" flood-opacity="0.5"/>
        </filter>
      </defs>

      <!-- Background silhouette - outer glow -->
      <path
        d="M50 3 
           C60 3 68 8 70 16
           C72 22 72 28 70 34
           C72 38 73 42 72 46
           L76 52 L73 65 L70 80
           L66 92 L58 98 L52 98 L46 98 L38 92 L34 80 L31 65 L28 52 L32 46
           C31 42 32 38 34 34
           C32 28 32 22 34 16
           C36 8 44 3 50 3 Z"
        :fill="primaryColor"
        fill-opacity="0.1"
        :stroke="primaryColor"
        stroke-width="0.3"
      />

      <!-- Main body silhouette -->
      <path
        d="M50 5 
           C58 5 66 10 68 18
           C70 24 70 30 68 36
           C70 40 71 44 70 48
           L74 54 L71 66 L68 80
           L64 90 L56 96 L52 96 L48 96 L40 90 L36 80 L33 66 L30 54 L34 48
           C33 44 34 40 36 36
           C34 30 34 24 36 18
           C38 10 46 5 50 5 Z"
        fill="url(#bodyGrad)"
        :stroke="primaryColor"
        stroke-width="0.6"
        filter="url(#glow)"
      />

      <!-- Head circle -->
      <circle
        cx="50"
        cy="12"
        r="8"
        fill="url(#bodyGrad)"
        :stroke="primaryColor"
        stroke-width="0.5"
        filter="url(#glow)"
      />

      <!-- Sensor zone circles -->
      <circle
        v-for="zone in sensorZones"
        :key="zone.id"
        :cx="zone.cx"
        :cy="zone.cy"
        :r="zone.r"
        fill="none"
        :stroke="primaryColor"
        stroke-width="0.4"
        stroke-dasharray="2,2"
        opacity="0.5"
      />

      <!-- Hit markers -->
      <g v-for="marker in hitMarkers" :key="marker.id">
        <!-- Outer glow -->
        <circle
          :cx="marker.x"
          :cy="marker.y"
          r="4"
          :fill="primaryColor"
          opacity="0.3"
        />
        <!-- Inner dot -->
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
</template>

<style scoped>
.target-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.1s ease;
}

.target-container.flash-active {
  background-color: rgba(0, 255, 0, 0.15);
}

.target-svg {
  width: 100%;
  height: 100%;
}
</style>
