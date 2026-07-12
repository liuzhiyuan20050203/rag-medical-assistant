<template>
  <article :class="['message', `${message.role}-message`]">
    <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
    <div class="bubble">
      <div v-if="message.type === 'loading'" class="loading-card">
        <div class="typing">
          <span></span>
          <span></span>
          <span></span>
          <strong>{{ loadingStageLabel }}</strong>
        </div>
        <div class="loading-steps" aria-label="分析进度">
          <span
            v-for="(stage, index) in visibleLoadingStages"
            :key="stage.key"
            :class="{ active: index === currentLoadingIndex, done: index < currentLoadingIndex }"
          >
            {{ stage.shortLabel }}
          </span>
        </div>
      </div>

      <template v-else>
        <div v-if="message.title || message.content" class="answer-content">
          <strong v-if="message.title">{{ message.title }}</strong>
          <pre v-if="message.content">{{ message.content }}</pre>
        </div>

        <div v-if="message.role === 'assistant' && hasClinicalPanels" class="assistant-panels">
          <div v-if="message.warning?.has_warning" class="message-panel warning-panel">
            <div class="panel-heading">
              <span>危险提醒</span>
              <b>优先处理</b>
            </div>
            <p>{{ message.warning.message }}</p>
            <div class="tag-list">
              <span v-for="item in message.warning.matched" :key="item">{{ item }}</span>
            </div>
          </div>

          <ReliabilityNote
            v-if="message.reliability"
            :reliability="message.reliability"
          />

          <SourceList v-if="message.docs?.length" :docs="message.docs" />

          <div v-if="message.followups?.length" class="message-panel followup-panel">
            <div class="panel-heading">
              <span>建议补充</span>
              <b>{{ message.followups.length }} 项</b>
            </div>
            <div class="followup-list">
              <button
                v-for="item in message.followups"
                :key="item"
                type="button"
                @click="$emit('append-followup', item)"
              >
                {{ item }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="message.role === 'assistant' && message.historyId" class="message-panel feedback-panel">
          <div class="panel-heading">
            <span>{{ message.feedbackStatus || '这次回答有帮助吗？' }}</span>
          </div>
          <div class="feedback-actions">
            <button
              v-for="item in feedbackOptions"
              :key="item.label"
              type="button"
              :class="{ active: message.feedbackType === item.label }"
              :disabled="message.feedbackLoading"
              @click="$emit('submit-feedback', message, item)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <AgentTracePanel v-if="isAdmin && message.trace" :message="message" />

        <div v-if="isAdmin && message.error" class="error-box">
          <strong>Agent 处理异常</strong>
          <p>{{ message.error.message }}</p>
          <span>{{ message.error.type }}</span>
        </div>

        <div v-if="interactive && message.role === 'assistant'" class="message-actions">
          <span
            v-if="message.llm"
            :class="['llm-badge', message.llm.used ? 'llm-on' : 'llm-off']"
          >
            {{ message.llm.used ? `AI 大模型参与：${message.llm.model || message.llm.provider || '已启用'}` : '本地知识库模板回答' }}
          </span>
          <button
            v-if="speechSynthesisSupported"
            type="button"
            @click="$emit('toggle-speak', message)"
          >
            {{ speakingMessageId === message.id ? '停止朗读' : '朗读回答' }}
          </button>
        </div>
      </template>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import AgentTracePanel from './AgentTracePanel.vue'
import ReliabilityNote from './ReliabilityNote.vue'
import SourceList from './SourceList.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
  isAdmin: {
    type: Boolean,
    default: false,
  },
  speechSynthesisSupported: {
    type: Boolean,
    default: false,
  },
  speakingMessageId: {
    type: String,
    default: '',
  },
  feedbackOptions: {
    type: Array,
    default: () => [],
  },
  interactive: {
    type: Boolean,
    default: true,
  },
})

defineEmits(['toggle-speak', 'submit-feedback', 'append-followup'])

const loadingStages = [
  { key: 'image', label: '图片线索识别中', shortLabel: '图片' },
  { key: 'safety', label: '危险症状筛查中', shortLabel: '筛查' },
  { key: 'retrieval', label: '知识库检索中', shortLabel: '检索' },
  { key: 'generation', label: '正在生成回答', shortLabel: '生成' },
]

const loadingStageKey = computed(() => props.message.loadingStage || 'safety')
const visibleLoadingStages = computed(() => (
  props.message.hasImageAnalysis
    ? loadingStages
    : loadingStages.filter((stage) => stage.key !== 'image')
))
const currentLoadingIndex = computed(() => {
  const index = visibleLoadingStages.value.findIndex((stage) => stage.key === loadingStageKey.value)
  return index >= 0 ? index : 0
})
const loadingStageLabel = computed(() => visibleLoadingStages.value[currentLoadingIndex.value]?.label || '正在分析你的描述')

const hasClinicalPanels = computed(() => Boolean(
  props.message.warning?.has_warning
  || props.message.reliability
  || props.message.docs?.length
  || props.message.followups?.length,
))
</script>

<style scoped>
.message {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 10px;
  max-width: 820px;
}

.user-message {
  align-self: flex-end;
  grid-template-columns: minmax(0, 1fr) 38px;
  max-width: min(720px, 86%);
}

.user-message .avatar {
  grid-column: 2;
  grid-row: 1;
}

.user-message .bubble {
  grid-column: 1;
  grid-row: 1;
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.avatar {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 8px;
  font-weight: 800;
}

.bubble {
  padding: 13px 15px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
}

.answer-content strong {
  display: block;
  margin-bottom: 6px;
}

.answer-content p,
.message-panel p {
  margin: 0;
  line-height: 1.8;
}

pre {
  margin: 0;
  color: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.72;
}

.loading-card {
  display: grid;
  gap: 12px;
}

.typing {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-secondary);
  font-weight: 700;
}

.typing span {
  width: 7px;
  height: 7px;
  background: var(--medical-blue);
  border-radius: 999px;
  animation: pulse 1s ease-in-out infinite;
}

.typing span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing span:nth-child(3) {
  animation-delay: 0.3s;
}

.loading-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 6px;
}

.loading-steps span {
  display: grid;
  min-height: 28px;
  place-items: center;
  color: var(--text-muted);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
}

.loading-steps span.done {
  color: #0f766e;
  background: #ecfdf5;
  border-color: #99f6e4;
}

.loading-steps span.active {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }

  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.assistant-panels {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.message-panel {
  display: grid;
  gap: 8px;
  padding: 10px;
  background: #f8fafc;
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
  color: var(--text-muted);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.warning-panel {
  color: #991b1b;
  background: #fff7ed;
  border-color: #fed7aa;
}

.warning-panel .panel-heading span {
  color: #9a3412;
}

.warning-panel .panel-heading b {
  color: #ffffff;
  background: #dc2626;
  border-color: #dc2626;
}

.error-box {
  margin-top: 14px;
  padding: 14px;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.error-box strong {
  margin-bottom: 4px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tag-list span {
  padding: 4px 9px;
  color: #ffffff;
  background: #dc2626;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.followup-list {
  display: grid;
  gap: 8px;
}

.followup-list button {
  padding: 10px 12px;
  color: #1d4ed8;
  text-align: left;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  cursor: pointer;
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--border);
}

.message-actions button {
  min-height: 34px;
  padding: 0 12px;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
}

.llm-badge {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
}

.llm-on {
  color: #166534;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.llm-off {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.feedback-panel {
  margin-top: 10px;
}

.feedback-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-actions button {
  min-height: 32px;
  padding: 0 10px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
}

.feedback-actions button:hover:not(:disabled),
.feedback-actions button.active {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #93c5fd;
}

.feedback-actions button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-box span {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 9px;
  color: #7f1d1d;
  background: #fee2e2;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 640px) {
  .message,
  .user-message {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .user-message {
    grid-template-columns: minmax(0, 1fr) 36px;
  }

  .avatar {
    width: 36px;
    height: 36px;
  }
}
</style>
