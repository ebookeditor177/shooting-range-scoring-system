<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import type { HitEvent } from '@/composables/useWebSocket'

const props = defineProps<{
  primaryColor?: string
  hitEffects?: boolean
}>()

const store = useGameStore()

// Sensor positions on the target silhouette (percentage-based)
const sensorZones = [
  { id: 'head', cx: 50, cy: 12, r: 10, label: 'HEAD', points: 100 },
  { id: 'chest', cx: 50, cy: 35, r: 14, label: 'CHEST', points: 50 },
  { id: 'stomach', cx: 50, cy: 55, r: 10, label: 'STOMACH', points: 30 },
  { id: 'left_leg', cx: 38, cy: 78, r: 7, label: 'L LEG', points: 20 },
  { id: 'right_leg', cx: 62, cy: 78, r: 7, label: 'R LEG', points: 20 }
]

// Hit markers to display
const hitMarkers = ref<{ position: string; x: number; y: number; id: number; opacity: number }[]>([])
let hitIdCounter = 0

// Flash effect state
const isFlashing = ref(false)

// Add hit marker when a hit event occurs
watch(() => store.recentHits, (hits) => {
  if (hits.length > 0) {
    const latestHit = hits[0]
    addHitMarker(latestHit)
  }
}, { deep: true })

function addHitMarker(hit: HitEvent) {
  const zone = sensorZones.find(z => z.id === hit.position)
  if (!zone) return

  // Add some randomness to hit position within the zone
  const randomOffset = () => (Math.random() - 0.5) * zone.r * 0.5
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
  if (hitMarkers.value.length > 20) {
    hitMarkers.value.shift()
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
          <stop offset="0%" :style="`stop-color:${primaryColor};stop-opacity:0.25`" />
          <stop offset="100%" :style="`stop-color:${primaryColor};stop-opacity:0.05`" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- Body silhouette - cleaner shape -->
      <path
        d="M50 4 
           C62 4 70 10 72 18
           C74 24 74 30 72 36
           L78 44 L74 54 L72 70
           L68 85 L62 96
           L56 96 L53 86
           L50 76
           L47 86 L44 96
           L38 96 L32 85 L28 70
           L26 54 L22 44 L28 36
           C26 30 26 24 28 18
           C30 10 38 4 50 4 Z"
        fill="url(#bodyGrad)"
        :stroke="primaryColor"
        stroke-width="0.8"
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
        stroke-width="0.5"
        stroke-dasharray="3,2"
        opacity="0.6"
      />

      <!-- Hit markers -->
      <g v-for="marker in hitMarkers" :key="marker.id">
        <circle
          :cx="marker.x"
          :cy="marker.y"
          r="2.5"
          :fill="primaryColor"
          filter="url(#glow)"
        >
          <animate
            attributeName="opacity"
            from="1"
            to="0"
            dur="1.5s"
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
