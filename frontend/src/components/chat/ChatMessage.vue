<template>
  <article :class="['message', `${message.role}-message`]">
    <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
    <div class="bubble">
      <!-- Loading state -->
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

      <!-- Content state -->
      <template v-else>
        <!-- 1. 紧急安全提醒 (最优先，置于最顶部，使用强层级红色视觉) -->
        <div
          v-if="message.role === 'assistant' && message.warning?.has_warning"
          class="emergency-warning-card"
        >
          <div class="emergency-header">
            <svg viewBox="0 0 24 24" class="emergency-icon" aria-hidden="true">
              <path d="M12 2L1 21h22L12 2zm1 14h-2v-2h2v2zm0-4h-2V8h2v4z" fill="currentColor"/>
            </svg>
            <strong>检测到疑似紧急危险症状</strong>
          </div>
          <p class="emergency-body">{{ message.warning.message }}</p>
          <div v-if="message.warning.matched?.length" class="emergency-tags">
            <span v-for="item in message.warning.matched" :key="item">{{ item }}</span>
          </div>
          <div class="emergency-action">
            <a href="tel:120" class="emergency-call-btn">立即联系急救服务或前往就近医疗机构</a>
          </div>
        </div>

        <!-- 2. AI 主要回答文本 (以文档卡片样式展示) -->
        <div v-if="message.title || message.content" class="answer-content">
          <strong v-if="message.title" class="answer-title">{{ message.title }}</strong>
          <pre v-if="message.content">{{ message.content }}</pre>
        </div>

        <!-- 3. AI 结构化临床辅助面板 -->
        <div v-if="message.role === 'assistant' && hasClinicalPanels" class="assistant-panels">
          <ReliabilityNote
            v-if="message.reliability"
            :reliability="message.reliability"
          />

          <SourceList v-if="message.docs?.length" :docs="message.docs" />

          <!-- 建议补充选项 -->
          <div v-if="message.followups?.length" class="message-panel followup-panel">
            <div class="panel-heading">
              <span>建议补充描述</span>
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

        <!-- 4. 反馈区 -->
        <div v-if="message.role === 'assistant' && message.historyId" class="message-panel feedback-panel">
          <div class="panel-heading">
            <span>{{ message.feedbackStatus || '这次回答对您有帮助吗？' }}</span>
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

        <!-- 5. 调试 Agent Trace -->
        <AgentTracePanel v-if="isAdmin && message.trace" :message="message" />

        <!-- 6. 异常提示 -->
        <div v-if="isAdmin && message.error" class="error-box">
          <strong>Agent 处理异常</strong>
          <p>{{ message.error.message }}</p>
          <span>{{ message.error.type }}</span>
        </div>

        <!-- 7. 工具条动作 -->
        <div v-if="interactive && message.role === 'assistant'" class="message-actions">
          <span
            v-if="message.llm"
            :class="['llm-badge', message.llm.used ? 'llm-on' : 'llm-off']"
          >
            {{ message.llm.used ? `AI 大模型参与：${message.llm.model || message.llm.provider || '已启用'}` : '本地知识库回答' }}
          </span>
          <button
            v-if="speechSynthesisSupported"
            type="button"
            class="speak-btn"
            @click="$emit('toggle-speak', message)"
          >
            {{ speakingMessageId === message.id ? '停止播放语音' : '播放语音' }}
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
  props.message.reliability
  || props.message.docs?.length
  || props.message.followups?.length,
))
</script>

<style scoped>
.message {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 16px;
  width: min(100%, 980px);
  align-self: flex-start;
  margin-bottom: 24px;
}

.user-message {
  width: fit-content;
  align-self: flex-end;
  grid-template-columns: minmax(0, 1fr) 42px;
  max-width: min(82%, 760px);
}

.user-message .avatar {
  grid-column: 2;
  grid-row: 1;
  background: var(--primary);
}

.user-message .bubble {
  grid-column: 1;
  grid-row: 1;
  color: var(--text-primary);
  background: var(--surface-container-high);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-xs) var(--radius-lg);
  padding: 16px 20px;
  font-size: 18px;
  line-height: 1.75;
  box-shadow: var(--shadow-sm);
}

.avatar {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--primary), var(--teal-bright));
  border-radius: 50%;
  font-weight: 800;
  font-size: 14px;
  box-shadow: var(--shadow-sm);
}

.bubble {
  min-width: 0;
}

.assistant-message .bubble {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

/* AI回答卡片样式 */
.answer-content {
  position: relative;
  padding: 24px 28px;
  overflow: hidden;
  background: rgba(0, 80, 203, 0.035);
  border: 1px solid var(--border);
  border-left: 4px solid var(--primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.answer-content:hover {
  border-color: #b3c5ff;
  border-left-color: var(--primary);
  box-shadow: 0 8px 24px rgba(0, 80, 203, 0.07);
}

.answer-title {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: var(--primary);
  margin-bottom: 12px;
}

pre {
  margin: 0;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 18px;
  line-height: 1.85;
}

/* 紧急红色危险卡片 */
.emergency-warning-card {
  padding: 18px 22px;
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  border-left: 5px solid var(--danger);
  border-radius: 12px;
  color: #7f1d1d;
  box-shadow: var(--shadow-sm);
}

.emergency-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 800;
  margin-bottom: 8px;
}

.emergency-icon {
  width: 22px;
  height: 22px;
  color: var(--danger);
}

.emergency-body {
  font-size: 15px;
  line-height: 1.6;
  margin: 0 0 12px 0;
  font-weight: 600;
}

.emergency-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.emergency-tags span {
  padding: 2px 8px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: var(--danger);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.emergency-action {
  display: flex;
}

.emergency-call-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 16px;
  background: var(--danger);
  color: #ffffff !important;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 800;
  font-size: 14px;
  transition: background-color 0.2s ease;
}

.emergency-call-btn:hover {
  background: #b91c1c;
}

.loading-card {
  padding: 18px 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  display: grid;
  gap: 12px;
  max-width: 500px;
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
  background: var(--primary);
  border-radius: 50%;
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
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
}

.loading-steps span.done {
  color: var(--teal);
  background: var(--teal-soft);
  border-color: #99f6e4;
}

.loading-steps span.active {
  color: #ffffff;
  background: var(--primary);
  border-color: var(--primary);
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.assistant-panels {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-panel {
  display: grid;
  gap: 8px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-heading span {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 800;
}

.panel-heading b {
  padding: 2px 8px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.followup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.followup-list button {
  padding: 10px 14px;
  color: var(--primary);
  text-align: left;
  background: var(--primary-soft);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  transition: all 0.2s ease;
}

.followup-list button:hover {
  background: #dbeafe;
}

.message-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.speak-btn {
  min-height: 32px;
  padding: 0 12px;
  color: var(--teal);
  background: var(--teal-soft);
  border: 1px solid #99f6e4;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
  font-size: 13px;
  transition: all 0.2s ease;
}

.speak-btn:hover {
  background: #ccfbf1;
}

.llm-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
}

.llm-on {
  color: var(--success-text);
  background: var(--success-soft);
  border-color: var(--success-border);
}

.llm-off {
  color: var(--warning-text);
  background: var(--warning-soft);
  border-color: var(--warning-border);
}

.feedback-panel {
  border-radius: 16px;
}

.feedback-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feedback-actions button {
  min-height: 32px;
  padding: 0 12px;
  color: var(--text-secondary);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  transition: all 0.2s ease;
}

.feedback-actions button:hover:not(:disabled),
.feedback-actions button.active {
  color: var(--primary);
  background: var(--primary-soft);
  border-color: var(--primary);
}

.feedback-actions button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-box {
  margin-top: 14px;
  padding: 16px;
  color: #991b1b;
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
}

.error-box strong {
  display: block;
  margin-bottom: 4px;
}

.error-box span {
  display: inline-block;
  margin-top: 8px;
  padding: 2px 8px;
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
    max-width: 100%;
  }

  .user-message {
    grid-template-columns: minmax(0, 1fr) 36px;
    max-width: 92%;
  }

  .avatar {
    width: 36px;
    height: 36px;
  }
}
</style>
