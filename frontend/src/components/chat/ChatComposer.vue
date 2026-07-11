<template>
  <div class="composer-container">
    <form
      class="composer-card"
      :class="{ focused: isFocused, disabled: loading }"
      @submit.prevent="$emit('submit')"
    >
      <div v-if="attachmentVisible || speechStatusText" class="composer-status-row">
        <div v-if="attachmentVisible" class="attachment-pill">
          <img v-if="imagePreview" :src="imagePreview" alt="已添加的图片" />
          <Paperclip v-else :size="17" aria-hidden="true" />
          <span>{{ attachmentLabel }}</span>
          <b v-if="imageLoading">识别中…</b>
          <button type="button" aria-label="移除附件" @click="$emit('clear-attachment')">
            <X :size="16" aria-hidden="true" />
          </button>
        </div>
        <span v-if="speechStatusText" class="voice-status">{{ speechStatusText }}</span>
      </div>

      <div class="composer-main-row">
        <button
          type="button"
          class="icon-action attach-action"
          title="添加药盒、检查单或症状图片"
          aria-label="添加图片"
          :disabled="loading || imageLoading"
          @click="openImagePicker"
        >
          <CirclePlus :size="29" aria-hidden="true" />
        </button>
        <input
          ref="imageInputRef"
          type="file"
          accept="image/*"
          class="sr-only"
          @change="handleImageFile"
        />

        <textarea
          ref="textareaRef"
          :value="modelValue"
          :placeholder="mainPlaceholder"
          rows="1"
          :disabled="loading"
          @input="updateQuestion"
          @focus="isFocused = true"
          @blur="isFocused = false"
          @keydown.enter.exact.prevent="$emit('submit')"
        ></textarea>

        <button
          type="button"
          class="icon-action voice-action"
          :class="{ active: isListening }"
          :disabled="!speechRecognitionSupported || loading"
          :title="isListening ? '停止语音识别' : '开始语音输入'"
          :aria-label="isListening ? '停止语音识别' : '开始语音输入'"
          @click="$emit('toggle-voice')"
        >
          <MicOff v-if="isListening" :size="28" aria-hidden="true" />
          <Mic v-else :size="28" aria-hidden="true" />
        </button>

        <button
          type="submit"
          class="send-button"
          :disabled="loading || imageLoading || !canSubmit"
          :title="loading || imageLoading ? '处理中' : '发送'"
        >
          <LoaderCircle v-if="loading || imageLoading" :size="22" class="spin" aria-hidden="true" />
          <template v-else>
            <span>发送</span>
            <Send :size="22" aria-hidden="true" />
          </template>
        </button>
      </div>

      <div class="composer-footer">
        <span>AI 生成内容仅供健康信息参考，请核对重要信息</span>
        <button type="button" :disabled="loading" @click="$emit('clear-conversation')">
          <Plus :size="16" aria-hidden="true" />
          新会话
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import {
  CirclePlus,
  LoaderCircle,
  Mic,
  MicOff,
  Paperclip,
  Plus,
  Send,
  X,
} from '@lucide/vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  attachmentVisible: { type: Boolean, default: false },
  imagePreview: { type: String, default: '' },
  attachmentLabel: { type: String, default: '' },
  imageLoading: { type: Boolean, default: false },
  speechStatusText: { type: String, default: '' },
  isListening: { type: Boolean, default: false },
  speechRecognitionSupported: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  canSubmit: { type: Boolean, default: false },
  mainPlaceholder: { type: String, default: '' },
})

const emit = defineEmits([
  'update:modelValue',
  'submit',
  'toggle-voice',
  'image-file',
  'clear-attachment',
  'clear-conversation',
])

const textareaRef = ref(null)
const imageInputRef = ref(null)
const isFocused = ref(false)

const resize = async () => {
  await nextTick()
  const textarea = textareaRef.value
  if (!textarea) return
  textarea.style.height = 'auto'
  const nextHeight = Math.min(textarea.scrollHeight, 148)
  textarea.style.height = `${nextHeight}px`
  textarea.style.overflowY = textarea.scrollHeight > 148 ? 'auto' : 'hidden'
}

const focus = () => textareaRef.value?.focus()

const updateQuestion = async (event) => {
  emit('update:modelValue', event.target.value)
  await resize()
}

const openImagePicker = () => imageInputRef.value?.click()

const handleImageFile = (event) => {
  const file = event.target.files?.[0]
  if (file) emit('image-file', file)
  event.target.value = ''
}

watch(() => props.modelValue, resize)

defineExpose({ focus, resize })
</script>

<style scoped>
.composer-container {
  padding: 18px 24px 14px;
  background: var(--surface);
  border-top: 1px solid var(--outline-variant);
}

.composer-card {
  position: relative;
  padding: 10px 12px 8px;
  background: var(--surface-soft);
  border: 2px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.composer-card.focused {
  border-color: var(--primary);
  box-shadow: 0 0 0 4px rgba(0, 80, 203, 0.1);
  transform: translateY(-1px);
}

.composer-card.disabled {
  opacity: 0.82;
}

.composer-main-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

textarea {
  width: 100%;
  min-width: 0;
  min-height: 54px;
  max-height: 148px;
  padding: 11px 4px;
  overflow-y: hidden;
  color: var(--text-primary);
  resize: none;
  background: transparent;
  border: 0;
  outline: 0;
  font-size: 18px;
  line-height: 1.7;
}

textarea::placeholder {
  color: var(--text-muted);
}

.icon-action {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.icon-action:hover:not(:disabled) {
  color: var(--primary);
  background: var(--primary-soft);
  transform: translateY(-1px);
}

.voice-action.active {
  color: #fff;
  background: var(--danger);
  animation: listeningPulse 1.4s ease-in-out infinite;
}

@keyframes listeningPulse {
  50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0.1); }
}

.send-button {
  display: inline-flex;
  min-width: 118px;
  min-height: 52px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 20px;
  color: #fff;
  background: var(--primary-bright);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 18px;
  font-weight: 850;
  box-shadow: 0 6px 14px rgba(0, 80, 203, 0.18);
  transition: background-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.send-button:hover:not(:disabled) {
  background: var(--primary);
  box-shadow: 0 8px 18px rgba(0, 80, 203, 0.24);
  transform: translateY(-1px);
}

.send-button:disabled,
.icon-action:disabled,
.composer-footer button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.composer-status-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 2px 4px 8px;
}

.attachment-pill {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  padding: 4px 7px 4px 9px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 700;
}

.attachment-pill img {
  width: 28px;
  height: 28px;
  object-fit: cover;
  border-radius: var(--radius-xs);
}

.attachment-pill span {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-pill b {
  font-size: 12px;
}

.attachment-pill button {
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: 50%;
  cursor: pointer;
}

.attachment-pill button:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.voice-status {
  color: var(--text-muted);
  font-size: 13px;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 4px 0;
  color: var(--text-muted);
  font-size: 12px;
}

.composer-footer button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  font-weight: 700;
}

.composer-footer button:hover:not(:disabled) {
  color: var(--primary);
}

.spin {
  animation: spin 1s linear infinite;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 640px) {
  .composer-container {
    padding: 10px;
  }

  .composer-card {
    padding: 7px;
  }

  .composer-main-row {
    gap: 4px;
  }

  textarea {
    min-height: 48px;
    padding: 9px 2px;
    font-size: 16px;
  }

  .icon-action {
    width: 40px;
    height: 44px;
  }

  .send-button {
    min-width: 48px;
    width: 48px;
    min-height: 46px;
    padding: 0;
  }

  .send-button span,
  .composer-footer > span {
    display: none;
  }

  .composer-footer {
    justify-content: flex-end;
  }
}
</style>
