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
  { id: 'head', cx: 50, cy: 15, r: 12, label: 'HEAD', points: 100 },
  { id: 'chest', cx: 50, cy: 40, r: 15, label: 'CHEST', points: 50 },
  { id: 'stomach', cx: 50, cy: 60, r: 12, label: 'STOMACH', points: 30 },
  { id: 'left_leg', cx: 35, cy: 80, r: 8, label: 'L LEG', points: 20 },
  { id: 'right_leg', cx: 65, cy: 80, r: 8, label: 'R LEG', points: 20 }
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
  }, 300)
}

const primaryColor = computed(() => props.primaryColor || store.config.primaryColor || '#00ff00')
</script>

<template>
  <div class="target-container" :class="{ 'flash-active': isFlashing }">
    <svg viewBox="0 0 100 100" class="target-svg">
      <!-- Target silhouette -->
      <defs>
        <linearGradient id="bodyGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" :style="`stop-color:${primaryColor};stop-opacity:0.3`" />
          <stop offset="100%" :style="`stop-color:${primaryColor};stop-opacity:0.1`" />
        </linearGradient>
      </defs>

      <!-- Body silhouette -->
      <path
        d="M50 5 
           C60 5 68 12 70 20
           C72 25 72 30 70 35
           L75 45 L72 55 L70 70
           L65 85 L60 95
           L55 95 L52 85
           L50 75
           L48 85 L45 95
           L40 95 L35 85 L30 70
           L28 55 L25 45 L30 35
           C28 30 28 25 30 20
           C32 12 40 5 50 5 Z"
        fill="url(#bodyGradient)"
        :stroke="primaryColor"
        stroke-width="0.5"
        class="body-outline"
      />

      <!-- Sensor zone circles (dashed) -->
      <circle
        v-for="zone in sensorZones"
        :key="zone.id"
        :cx="zone.cx"
        :cy="zone.cy"
        :r="zone.r"
        fill="none"
        :stroke="primaryColor"
        stroke-width="0.3"
        stroke-dasharray="2,1"
        class="sensor-zone"
      />

      <!-- Hit markers -->
      <g v-for="marker in hitMarkers" :key="marker.id">
        <circle
          :cx="marker.x"
          :cy="marker.y"
          r="3"
          :fill="primaryColor"
          class="hit-marker"
        >
          <animate
            attributeName="opacity"
            from="1"
            to="0"
            dur="1s"
            begin="0s"
            fill="freeze"
          />
        </circle>
        <!-- Hit score popup -->
        <text
          :x="marker.x + 4"
          :y="marker.y - 4"
          :fill="primaryColor"
          font-size="3"
          class="hit-score"
        >
          +{{ store.recentHits.find(h => h.position === marker.position)?.score || 0 }}
        </text>
      </g>

      <!-- Labels -->
      <text
        v-for="zone in sensorZones"
        :key="'label-' + zone.id"
        :x="zone.cx"
        :y="zone.cy + zone.r + 3"
        :fill="primaryColor"
        font-size="2"
        text-anchor="middle"
        class="zone-label"
      >
        {{ zone.label }}
      </text>
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
  transition: background-color 0.15s ease;
}

.target-container.flash-active {
  background-color: rgba(0, 255, 0, 0.2);
}

.target-svg {
  width: 90%;
  height: 90%;
  max-width: 500px;
  max-height: 800px;
}

.body-outline {
  transition: stroke-width 0.3s ease;
}

.sensor-zone {
  opacity: 0.5;
}

.hit-marker {
  filter: drop-shadow(0 0 3px currentColor);
}

.hit-score {
  animation: score-float 1s ease-out forwards;
}

.zone-label {
  opacity: 0.7;
  font-weight: bold;
}

@keyframes score-float {
  0% {
    transform: translateY(0);
    opacity: 1;
  }
  100% {
    transform: translateY(-10px);
    opacity: 0;
  }
}
</style>
