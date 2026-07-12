<template>
  <div v-if="reliability" :class="['reliability-note', reliabilityClass]">
    <div class="panel-heading">
      <span>回答可靠性</span>
      <b>{{ reliability.label || reliabilityLevelLabel(reliability.level) }}</b>
    </div>
    <p>{{ reliability.message }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  reliability: {
    type: Object,
    default: null,
  },
})

const reliabilityLabels = {
  high: '资料匹配充分',
  medium: '资料匹配一般',
  low: '依据偏弱',
  insufficient: '依据不足',
}

const reliabilityLevelLabel = (level) => reliabilityLabels[level] || '待评估'

const reliabilityClass = computed(() => `reliability-${props.reliability?.level || 'unknown'}`)
</script>

<style scoped>
.reliability-note {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-heading span {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 900;
}

.panel-heading b {
  flex: 0 0 auto;
  padding: 2px 8px;
  background: #ffffff;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.reliability-note p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.reliability-high {
  background: #ecfdf5;
  border-color: #99f6e4;
}

.reliability-high .panel-heading b {
  color: #0f766e;
}

.reliability-medium {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.reliability-medium .panel-heading b {
  color: #1d4ed8;
}

.reliability-low,
.reliability-insufficient,
.reliability-unknown {
  background: #fff7ed;
  border-color: #fed7aa;
}

.reliability-low .panel-heading b,
.reliability-insufficient .panel-heading b,
.reliability-unknown .panel-heading b {
  color: #c2410c;
}
</style>
