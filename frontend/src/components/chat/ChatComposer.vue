<template>
  <form class="composer" @submit.prevent="$emit('submit')">
    <div v-if="attachmentVisible || speechStatusText" class="composer-status">
      <div v-if="attachmentVisible" class="attachment-pill">
        <img v-if="imagePreview && attachmentKind !== 'video'" :src="imagePreview" alt="已添加的图片" />
        <Video v-else-if="attachmentKind === 'video'" :size="18" aria-hidden="true" />
        <Paperclip v-else :size="18" aria-hidden="true" />
        <span>{{ attachmentLabel }}</span>
        <b v-if="imageLoading">处理中</b>
        <button type="button" title="移除附件" aria-label="移除附件" @click="$emit('clear-attachment')">
          <X :size="16" aria-hidden="true" />
        </button>
      </div>

      <span v-if="speechStatusText" class="subtle-status">{{ speechStatusText }}</span>
    </div>

    <div class="chat-composer-bar">
      <button
        type="button"
        class="icon-btn voice-btn"
        :class="{ active: isListening }"
        :disabled="!speechRecognitionSupported"
        :title="isListening ? '停止语音输入' : '语音输入'"
        :aria-label="isListening ? '停止语音输入' : '语音输入'"
        @click="$emit('toggle-voice')"
      >
        <MicOff v-if="isListening" :size="22" aria-hidden="true" />
        <Mic v-else :size="22" aria-hidden="true" />
        <span>{{ isListening ? '停止' : '语音' }}</span>
      </button>

      <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="mainPlaceholder"
        rows="1"
        @input="updateQuestion"
        @keydown.enter.exact.prevent="$emit('submit')"
      ></textarea>

      <input
        ref="imageInputRef"
        type="file"
        accept="image/*"
        class="sr-only"
        @change="handleImageFile"
      />

      <input
        ref="videoInputRef"
        type="file"
        accept="video/*"
        class="sr-only"
        @change="handleVideoFile"
      />

      <button
        type="button"
        class="icon-btn"
        title="添加图片"
        aria-label="添加图片"
        :disabled="loading || imageLoading"
        @click="openImagePicker"
      >
        <Image :size="22" aria-hidden="true" />
        <span>图片</span>
      </button>

      <button
        type="button"
        class="icon-btn"
        title="添加视频"
        aria-label="添加视频"
        :disabled="loading || imageLoading"
        @click="openVideoPicker"
      >
        <Video :size="22" aria-hidden="true" />
        <span>视频</span>
      </button>

      <button
        type="submit"
        class="icon-btn send-btn"
        :disabled="loading || imageLoading || !canSubmit"
        :title="loading || imageLoading ? '处理中' : '发送'"
        :aria-label="loading || imageLoading ? '处理中' : '发送'"
      >
        <LoaderCircle v-if="loading || imageLoading" :size="22" aria-hidden="true" />
        <Send v-else :size="22" aria-hidden="true" />
        <span>{{ loading || imageLoading ? '处理中' : '发送' }}</span>
      </button>
    </div>
  </form>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import {
  Image,
  LoaderCircle,
  Mic,
  MicOff,
  Paperclip,
  Send,
  Video,
  X,
} from '@lucide/vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  attachmentVisible: {
    type: Boolean,
    default: false,
  },
  imagePreview: {
    type: String,
    default: '',
  },
  attachmentKind: {
    type: String,
    default: 'image',
  },
  attachmentLabel: {
    type: String,
    default: '',
  },
  imageLoading: {
    type: Boolean,
    default: false,
  },
  speechStatusText: {
    type: String,
    default: '',
  },
  isListening: {
    type: Boolean,
    default: false,
  },
  speechRecognitionSupported: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  canSubmit: {
    type: Boolean,
    default: false,
  },
  mainPlaceholder: {
    type: String,
    default: '',
  },
})

const emit = defineEmits([
  'update:modelValue',
  'submit',
  'toggle-voice',
  'image-file',
  'video-file',
  'clear-attachment',
])

const textareaRef = ref(null)
const imageInputRef = ref(null)
const videoInputRef = ref(null)

const resize = async () => {
  await nextTick()
  const textarea = textareaRef.value
  if (!textarea) return

  textarea.style.height = 'auto'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`
}

const focus = () => {
  textareaRef.value?.focus()
}

const updateQuestion = async (event) => {
  emit('update:modelValue', event.target.value)
  await resize()
}

const openImagePicker = () => {
  imageInputRef.value?.click()
}

const openVideoPicker = () => {
  videoInputRef.value?.click()
}

const handleImageFile = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    emit('image-file', file)
  }
  event.target.value = ''
}

const handleVideoFile = (event) => {
  const file = event.target.files?.[0]
  if (file) {
    emit('video-file', file)
  }
  event.target.value = ''
}

watch(
  () => props.modelValue,
  () => {
    resize()
  },
)

defineExpose({
  focus,
  resize,
})
</script>

<style scoped>
.composer {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #ffffff;
  border-top: 1px solid var(--border);
}

.composer-status {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.attachment-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: min(100%, 520px);
  min-height: 42px;
  padding: 5px 8px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 13px;
}

.attachment-pill img {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 999px;
}

.attachment-pill span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-pill b {
  flex: 0 0 auto;
  color: #1d4ed8;
  font-size: 12px;
}

.attachment-pill button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
}

.attachment-pill button:hover {
  color: #991b1b;
  background: #fee2e2;
}

.subtle-status {
  color: var(--text-muted);
  font-size: 13px;
}

.chat-composer-bar {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) 58px 58px 64px;
  gap: 8px;
  align-items: end;
  padding: 8px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

textarea {
  width: 100%;
  min-height: 46px;
  max-height: 150px;
  padding: 12px 4px;
  color: var(--text-primary);
  resize: none;
  overflow-y: auto;
  background: transparent;
  border: 0;
  border-radius: 8px;
  outline: none;
}

textarea:focus {
  box-shadow: none;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  white-space: nowrap;
  border: 0;
  clip: rect(0 0 0 0);
}

.icon-btn {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 50px;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.icon-btn span {
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
}

.voice-btn {
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
}

.voice-btn.active {
  color: #ffffff;
  background: #dc2626;
  border-color: #dc2626;
}

.voice-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.icon-btn:hover:not(:disabled) {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #93c5fd;
  transform: translateY(-1px);
}

.send-btn {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.send-btn:hover:not(:disabled) {
  color: #ffffff;
  background: var(--medical-blue);
  border-color: var(--medical-blue);
}

.send-btn svg {
  animation: none;
  transform: translateX(1px);
}

.send-btn:disabled,
.icon-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.send-btn:disabled svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .chat-composer-bar {
    grid-template-columns: 46px minmax(0, 1fr) 46px 46px 52px;
    gap: 6px;
  }

  .icon-btn {
    height: 46px;
  }

  .icon-btn span {
    display: none;
  }
}
</style>
