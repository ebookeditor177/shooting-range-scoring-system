<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useGameStore } from '@/stores/gameStore'

const props = defineProps<{
  laneNumber: number
  targetScore?: number
  primaryColor?: string
}>()

const store = useGameStore()

const displayScore = ref(0)
const scoreAnimation = ref(false)

// Animate score changes
watch(() => store.currentScore(props.laneNumber), (newScore) => {
  if (newScore > displayScore.value) {
    scoreAnimation.value = true
    setTimeout(() => {
      scoreAnimation.value = false
    }, 300)
  }
  displayScore.value = newScore
}, { immediate: true })

const progress = computed(() => {
  if (!props.targetScore) return 0
  return Math.min((displayScore.value / props.targetScore) * 100, 100)
})

const primaryColor = computed(() => props.primaryColor || store.config.primaryColor || '#00ff00')
</script>

<template>
  <div class="score-display">
    <div class="score-main">
      <span class="score-label">SCORE</span>
      <span 
        class="score-value" 
        :class="{ 'score-animate': scoreAnimation }"
        :style="{ color: primaryColor }"
      >
        {{ displayScore }}
      </span>
    </div>

    <div class="score-details" v-if="targetScore">
      <div class="progress-bar">
        <div 
          class="progress-fill"
          :style="{ 
            width: `${progress}%`,
            backgroundColor: primaryColor 
          }"
        ></div>
      </div>
      <div class="score-target">
        Target: {{ targetScore }}
      </div>
    </div>

    <div class="hit-count">
      <span class="hits-label">HITS</span>
      <span class="hits-value">{{ store.totalHits(laneNumber) }}</span>
    </div>
  </div>
</template>

<style scoped>
.score-display {
  background: rgba(0, 0, 0, 0.8);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px 30px;
  text-align: center;
}

.score-main {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.score-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 3px;
  font-weight: bold;
}

.score-value {
  font-size: 72px;
  font-weight: bold;
  text-shadow: 0 0 20px currentColor;
  transition: transform 0.15s ease;
}

.score-value.score-animate {
  transform: scale(1.1);
}

.score-details {
  margin-top: 15px;
}

.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.score-target {
  margin-top: 8px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

.hit-count {
  margin-top: 15px;
  display: flex;
  justify-content: center;
  gap: 10px;
  font-size: 16px;
}

.hits-label {
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 2px;
}

.hits-value {
  font-weight: bold;
}
</style>
