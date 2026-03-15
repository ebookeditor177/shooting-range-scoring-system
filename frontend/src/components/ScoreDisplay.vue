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

// Animate score changes
watch(() => store.currentScore(props.laneNumber), (newScore) => {
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
      <span class="score-value" :style="{ color: primaryColor }">
        {{ displayScore }}
      </span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: `${progress}%`, backgroundColor: primaryColor }"></div>
    </div>
    <div class="score-meta">
      <span>{{ store.totalHits(props.laneNumber) }} HITS</span>
      <span>TARGET: {{ targetScore || 1000 }}</span>
    </div>
  </div>
</template>

<style scoped>
.score-display {
  background: rgba(0, 0, 0, 0.8);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 24px 40px;
  text-align: center;
}

.score-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 4px;
  font-weight: 600;
}

.score-value {
  display: block;
  font-size: 64px;
  font-weight: 900;
  text-shadow: 0 0 30px currentColor;
  line-height: 1.1;
}

.progress-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 16px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 3px;
}

.score-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 1px;
}
</style>
