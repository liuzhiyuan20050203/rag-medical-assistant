<template>
  <div class="chat-page">
    <section class="chat-shell">
      <!-- Top fold panel: history sessions -->
      <aside class="chat-side">
        <div class="side-primary-actions">
          <button type="button" class="new-session-btn" :disabled="loading" @click="startNewConversation">
            <Plus :size="24" aria-hidden="true" />
            <span>新建对话</span>
          </button>
        </div>

        <button
          type="button"
          class="side-toggle"
          :aria-expanded="sidePanelOpen"
          aria-controls="chat-history-panel"
          @click="sidePanelOpen = !sidePanelOpen"
        >
          <ChevronDown :class="{ open: sidePanelOpen }" :size="16" aria-hidden="true" />
          <span>历史会话</span>
          <small v-if="currentUser">{{ conversationSessions.length }}</small>
        </button>

        <div id="chat-history-panel" :class="['side-content', { open: sidePanelOpen }]">
          <div class="session-panel">
            <div class="section-title">
              <div>
                <strong>最近会话</strong>
                <span v-if="currentUser">{{ conversationSessions.length }}</span>
              </div>
              <button type="button" :disabled="sessionsLoading" @click="loadConversationSessions">
                <RefreshCw :size="14" aria-hidden="true" />
                {{ sessionsLoading ? '刷新中' : '刷新' }}
              </button>
            </div>

            <label v-if="currentUser && conversationSessions.length" class="session-search">
              <Search :size="15" aria-hidden="true" />
              <input
                v-model="sessionSearch"
                type="search"
                placeholder="搜索历史会话"
                aria-label="搜索历史会话"
              />
              <button v-if="sessionSearch" type="button" aria-label="清空历史会话搜索" @click="sessionSearch = ''">
                <X :size="14" aria-hidden="true" />
              </button>
            </label>

            <div v-if="!currentUser" class="session-empty">
              {{ isGuest ? '游客模式可直接咨询，登录后可保存并继续历史会话。' : '登录后会自动保存历史会话，并可从这里继续对话。' }}
            </div>
            <div v-else-if="sessionsLoading" class="session-empty">
              正在加载历史会话...
            </div>
            <div v-else-if="conversationSessions.length === 0" class="session-empty">
              暂无历史会话，发送第一条消息后会自动保存。
            </div>
            <div v-else-if="filteredConversationSessions.length === 0" class="session-empty">
              没有找到与“{{ sessionSearch }}”匹配的会话。
            </div>
            <div v-else class="session-list">
              <button
                v-for="session in filteredConversationSessions"
                :key="session.id"
                type="button"
                :class="{ active: Number(activeSessionId) === Number(session.id) }"
                @click="openConversationSession(session.id)"
              >
                <HistoryIcon :size="15" aria-hidden="true" />
                <span>{{ session.title || `会话 #${session.id}` }}</span>
                <small>{{ session.message_count || 0 }} 条消息</small>
              </button>
            </div>

            <p v-if="sessionsStatus && currentUser" class="session-status">{{ sessionsStatus }}</p>
          </div>
        </div>
      </aside>

      <!-- Main chat area -->
      <main class="chat-main">
        <header class="chat-header">
          <div class="assistant-identity">
            <span class="assistant-icon" aria-hidden="true">
              <Bot :size="27" :stroke-width="2.2" />
            </span>
            <span>
              <strong>MedAgent 智能咨询</strong>
              <small><i></i>智能助手已就绪</small>
            </span>
          </div>
          <button type="button" class="chat-menu-button" aria-label="更多咨询选项">
            <MoreHorizontal :size="27" aria-hidden="true" />
          </button>
        </header>

        <div ref="conversationRef" class="conversation">
          <!-- Empty conversation state -->
          <div v-if="messages.length === 0" class="empty-conversation-state">
            <div class="empty-icon-wrap">
              <svg class="med-cross-icon" viewBox="0 0 24 24" role="img">
                <path d="M19 10.5h-5.5V5c0-.8-.7-1.5-1.5-1.5s-1.5.7-1.5 1.5v5.5H5c-.8 0-1.5.7-1.5 1.5s.7 1.5 1.5 1.5h5.5V19c0 .8.7 1.5 1.5 1.5s1.5-.7 1.5-1.5v-5.5H19c.8 0 1.5-.7 1.5-1.5s-.7-1.5-1.5-1.5z" fill="currentColor"/>
              </svg>
            </div>
            <h2>今天想咨询什么？</h2>
            <p class="empty-subtitle">
              请尽量说明症状部位、持续时间、年龄以及是否正在服药，AI 将结合健康知识库为您整理参考建议。
            </p>
            <div class="quick-prompts-grid">
              <button type="button" class="quick-prompt-card" @click="triggerQuickConsult('我最近总是头痛，尤其是晚上，已经持续三天了。该怎么护理？')">
                <span class="prompt-title">感冒发热</span>
                <span class="prompt-desc">头痛、发烧38.5℃的护理与用药建议</span>
              </button>
              <button type="button" class="quick-prompt-card" @click="triggerQuickConsult('请帮我核对布洛芬的服用禁忌、适用人群和注意事项。')">
                <span class="prompt-title">药品禁忌</span>
                <span class="prompt-desc">了解布洛芬的适用情况和禁用人群</span>
              </button>
              <button type="button" class="quick-prompt-card" @click="triggerQuickConsult('血常规报告中白细胞计数偏高，通常是什么原因？')">
                <span class="prompt-title">检查单解读</span>
                <span class="prompt-desc">分析血常规指标偏高的潜在临床意义</span>
              </button>
              <button type="button" class="quick-prompt-card" @click="triggerQuickConsult('手臂上突然出现红斑并伴随瘙痒，如何作应急处理？')">
                <span class="prompt-title">皮肤症状</span>
                <span class="prompt-desc">急性过敏性皮肤症状的初步建议</span>
              </button>
            </div>
          </div>

          <!-- Message list -->
          <template v-else>
            <ChatMessage
              v-for="message in messages"
              :key="message.id"
              :message="message"
              :is-admin="isAdmin"
              :speech-synthesis-supported="speechSynthesisSupported"
              :speaking-message-id="speakingMessageId"
              :feedback-options="feedbackOptions"
              @toggle-speak="toggleSpeak"
              @submit-feedback="submitFeedback"
              @append-followup="appendFollowup"
            />
          </template>
        </div>

        <!-- Composer area -->
        <ChatComposer
          ref="composerRef"
          v-model="question"
          :attachment-visible="attachmentVisible"
          :image-preview="imagePreview"
          :attachment-label="attachmentLabel"
          :image-loading="imageLoading"
          :speech-status-text="speechStatusText"
          :is-listening="isListening"
          :speech-recognition-supported="speechRecognitionSupported"
          :loading="loading"
          :can-submit="canSubmit"
          :main-placeholder="mainPlaceholder"
          @submit="submitQuestion"
          @toggle-voice="toggleVoiceInput"
          @image-file="handleImageFile"
          @clear-attachment="clearAttachment"
          @clear-conversation="startNewConversation"
        />

        <section class="safety-note">
          <strong>安全提示：</strong>
          本系统仅提供健康信息参考，不能替代医生诊断或药师指导。若出现胸痛、呼吸困难、高热不退、意识模糊等情况，请及时就医。
        </section>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bot,
  ChevronDown,
  History as HistoryIcon,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  X,
} from '@lucide/vue'
import { apiUrl, clearPageCacheByPrefix } from '../api'
import ChatComposer from '../components/chat/ChatComposer.vue'
import ChatMessage from '../components/chat/ChatMessage.vue'
import { useChatSession } from '../composables/useChatSession'
import { useSpeechInput } from '../composables/useSpeechInput'

const route = useRoute()
const router = useRouter()

const feedbackOptions = [
  { label: '有帮助', rating: 5, text: '有帮助' },
  { label: '不准确', rating: 1, text: '回答不准确' },
  { label: '太慢', rating: 2, text: '响应速度太慢' },
  { label: '没看懂图片', rating: 1, text: '图片识别或图片理解不准确' },
  { label: '答非所问', rating: 1, text: '回答和问题不匹配' },
]

const inputType = ref('text')
const question = ref('')
const imageSummary = ref('')
const imageTagsText = ref('')
const imagePreview = ref('')
const imageFileName = ref('')
const imageFileRef = ref(null)
const imageLoading = ref(false)
const imageStatus = ref('')
const loading = ref(false)
const conversationRef = ref(null)
const composerRef = ref(null)
const speechSynthesisSupported = ref(false)
const speakingMessageId = ref('')
const sidePanelOpen = ref(false)
const sessionSearch = ref('')
const loadingStageTimers = []

const scrollToBottom = async () => {
  await nextTick()
  const el = conversationRef.value
  if (el) {
    el.scrollTo({
      top: el.scrollHeight,
      behavior: 'smooth',
    })
  }
}

const {
  messages,
  currentUser,
  isGuest,
  activeSessionId,
  conversationSessions,
  sessionsLoading,
  sessionsStatus,
  restoreStatus,
  isAdmin,
  authHeaders,
  loadCurrentUser,
  saveChatCache,
  clearCurrentConversation,
  loadConversationSessions,
  restoreChatCache,
  restoreSessionFromServer,
} = useChatSession({ scrollToBottom })

const {
  isListening,
  speechStatus,
  speechRecognitionSupported,
  refreshSpeechSupport,
  toggleVoiceInput,
  stopRecognition,
} = useSpeechInput(question)

const canSubmit = computed(() => {
  return Boolean(
    question.value.trim()
    || imagePreview.value
    || imageFileRef.value
    || imageSummary.value.trim()
    || imageTagsText.value.trim()
  )
})

const filteredConversationSessions = computed(() => {
  const query = sessionSearch.value.trim().toLowerCase()
  if (!query) return conversationSessions.value

  return conversationSessions.value.filter((session) => [
    session.title,
    session.id,
    session.message_count,
  ].filter((value) => value !== undefined && value !== null).join(' ').toLowerCase().includes(query))
})

const attachmentVisible = computed(() => Boolean(imagePreview.value || imageFileName.value || imageStatus.value))

const attachmentLabel = computed(() => {
  if (imageLoading.value) return imageFileName.value ? `正在识别 ${imageFileName.value}` : '正在识别图片'
  if (imageFileName.value && !imagePreview.value && !imageFileRef.value) return `图片未读取成功，请重新选择 ${imageFileName.value}`
  if (imageStatus.value && !imagePreview.value && !imageFileRef.value) return imageStatus.value
  if (imageSummary.value || imageTagsText.value) return imageFileName.value ? `已添加 ${imageFileName.value}` : '已添加图片'
  if (imageFileName.value) return `已选择 ${imageFileName.value}`
  return '已添加附件'
})

const mainPlaceholder = computed(() => '请输入症状描述、用药疑问或健康咨询，可附加药盒/报告图片...')

const speechStatusText = computed(() => {
  if (!speechRecognitionSupported.value) return '当前浏览器不支持语音识别，建议使用 Chrome 或 Edge。'
  if (speechStatus.value) return speechStatus.value
  if (restoreStatus.value) return restoreStatus.value
  return ''
})

const resizeComposer = async () => {
  await composerRef.value?.resize()
}

const focusComposer = () => {
  composerRef.value?.focus()
}

const invalidateHistoryCaches = () => {
  clearPageCacheByPrefix('history:list:')
  clearPageCacheByPrefix('admin:')
  clearPageCacheByPrefix('analytics:')
  clearPageCacheByPrefix('home:')
}

const clearLoadingStageTimers = () => {
  while (loadingStageTimers.length) {
    window.clearTimeout(loadingStageTimers.pop())
  }
}

const updateLoadingStage = (loadingId, stage) => {
  const loadingMessage = messages.value.find((item) => item.id === loadingId)
  if (loadingMessage?.type === 'loading') {
    loadingMessage.loadingStage = stage
  }
}

const scheduleLoadingStages = (loadingId, hasImageAnalysis) => {
  clearLoadingStageTimers()
  const stages = hasImageAnalysis
    ? [
        { delay: 0, stage: 'image' },
        { delay: 1000, stage: 'safety' },
        { delay: 1900, stage: 'retrieval' },
        { delay: 3200, stage: 'generation' },
      ]
    : [
        { delay: 0, stage: 'safety' },
        { delay: 1100, stage: 'retrieval' },
        { delay: 2600, stage: 'generation' },
      ]

  stages.forEach(({ delay, stage }) => {
    loadingStageTimers.push(window.setTimeout(() => updateLoadingStage(loadingId, stage), delay))
  })
}

const parseImageTags = () => imageTagsText.value
  .split(/[，,、;；\s]+/)
  .map((item) => item.trim())
  .filter(Boolean)

const readFileAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })

const compressImageFile = (file, maxSize = 1024, quality = 0.76) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    const timeout = window.setTimeout(() => {
      reject(new Error('图片读取超时'))
    }, 8000)
    const finish = (callback, value) => {
      window.clearTimeout(timeout)
      callback(value)
    }
    reader.onload = () => {
      const img = new window.Image()
      img.onload = () => {
        const scale = Math.min(1, maxSize / Math.max(img.width, img.height))
        const width = Math.max(1, Math.round(img.width * scale))
        const height = Math.max(1, Math.round(img.height * scale))
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, width, height)
        finish(resolve, canvas.toDataURL('image/jpeg', quality))
      }
      img.onerror = () => finish(reject, new Error('图片解码失败'))
      img.src = String(reader.result || '')
    }
    reader.onerror = () => finish(reject, new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })

const prepareImagePreview = async (file) => {
  try {
    return await compressImageFile(file)
  } catch (error) {
    console.warn('图片压缩失败，改用原图读取。', error)
    return readFileAsDataUrl(file)
  }
}

const isImageFile = (file) => {
  const type = String(file?.type || '').toLowerCase()
  const name = String(file?.name || '').toLowerCase()
  return type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp|heic|heif)$/i.test(name)
}

const stopSpeaking = () => {
  if (!speechSynthesisSupported.value) return
  window.speechSynthesis.cancel()
  speakingMessageId.value = ''
}

const toggleSpeak = (message) => {
  speechSynthesisSupported.value = 'speechSynthesis' in window

  if (!speechSynthesisSupported.value || !message?.content) return

  if (speakingMessageId.value === message.id) {
    stopSpeaking()
    return
  }

  stopSpeaking()
  const utterance = new SpeechSynthesisUtterance(message.content)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.92
  utterance.pitch = 1
  utterance.onend = () => {
    speakingMessageId.value = ''
  }
  utterance.onerror = () => {
    speakingMessageId.value = ''
  }
  speakingMessageId.value = message.id
  window.speechSynthesis.speak(utterance)
}

const submitFeedback = async (message, option) => {
  if (!message?.historyId || message.feedbackLoading) return

  message.feedbackLoading = true
  message.feedbackStatus = '正在保存反馈...'

  try {
    const response = await fetch(apiUrl(`/api/history/${message.historyId}/feedback`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        rating: option.rating,
        feedback_text: option.text,
      }),
    })
    const data = await response.json()

    if (!data.success) {
      message.feedbackStatus = data.message || '反馈保存失败'
      return
    }

    message.feedbackType = option.label
    message.feedbackStatus = option.label === '有帮助'
      ? '谢谢反馈，我们会继续保持。'
      : '已记录问题，管理员可在后台复核。'
  } catch (error) {
    message.feedbackStatus = '反馈保存失败，请稍后再试。'
    console.error(error)
  } finally {
    message.feedbackLoading = false
  }
}

const handleImageFile = async (file) => {
  if (!file) return

  clearAttachment()

  if (!isImageFile(file)) {
    imageStatus.value = '请选择图片文件。'
    return
  }

  inputType.value = question.value.trim() ? 'mixed' : 'image'
  imageFileName.value = file.name
  imageFileRef.value = file
  imageStatus.value = '正在读取图片...'
  try {
    imagePreview.value = await prepareImagePreview(file)
    imageStatus.value = '图片已添加，发送后会和文字一起分析。'
  } catch (error) {
    console.error(error)
    imagePreview.value = ''
    imageFileName.value = ''
    imageFileRef.value = null
    imageStatus.value = '图片读取失败，请重新选择图片。'
  }
}

const clearAttachment = () => {
  imageSummary.value = ''
  imageTagsText.value = ''
  imagePreview.value = ''
  imageFileName.value = ''
  imageFileRef.value = null
  imageStatus.value = ''
}

const buildImageSummary = (result) => {
  const lines = []
  const answer = result?.answer || {}
  const llmAnalysis = result?.llm?.analysis || {}

  if (llmAnalysis.summary) {
    lines.push(llmAnalysis.summary)
  } else if (answer.summary) {
    lines.push(answer.summary)
  }

  if (Array.isArray(llmAnalysis.visible_findings) && llmAnalysis.visible_findings.length) {
    lines.push(`可见信息：${llmAnalysis.visible_findings.slice(0, 6).join('；')}`)
  } else if (Array.isArray(answer.evidence) && answer.evidence.length) {
    lines.push(`可见信息：${answer.evidence.slice(0, 5).join('；')}`)
  } else if (Array.isArray(result?.observations) && result.observations.length) {
    lines.push(`画面质量：${result.observations.slice(0, 3).join('；')}`)
  }

  if (llmAnalysis.likely_scene) {
    lines.push(`可能场景：${llmAnalysis.likely_scene}`)
  }

  if (Array.isArray(llmAnalysis.quality_warnings) && llmAnalysis.quality_warnings.length) {
    lines.push(`图片质量提示：${llmAnalysis.quality_warnings.slice(0, 2).join('；')}`)
  }

  if (Array.isArray(llmAnalysis.recommended_questions) && llmAnalysis.recommended_questions.length) {
    lines.push(`建议补充：${llmAnalysis.recommended_questions.slice(0, 2).join('；')}`)
  } else if (Array.isArray(answer.follow_up_questions) && answer.follow_up_questions.length) {
    lines.push(`建议补充：${answer.follow_up_questions.slice(0, 2).join('；')}`)
  }

  return lines.filter(Boolean).join('\n')
}

const analyzeImageForChat = async (noteText = '') => {
  if (!imagePreview.value || imageLoading.value) return false

  imageLoading.value = true
  imageStatus.value = '正在识别图片...'

  try {
    const response = await fetch(apiUrl('/api/multimodal/image/analyze'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image: imagePreview.value,
        file_name: imageFileName.value,
        note: noteText || question.value,
      }),
    })
    const data = await response.json()

    if (!response.ok || !data.success) {
      imageStatus.value = data.message || `图片识别失败，状态码：${response.status}`
      return false
    }

    if (!data.llm?.success || !data.llm?.analysis) {
      imageStatus.value = data.llm?.error || '视觉大模型没有返回有效识别结果，请检查模型配置或换一张更清晰的图片。'
      return false
    }

    const llmAnalysis = data.llm?.analysis || {}
    const tags = [
      ...(data.tags || []),
      llmAnalysis.likely_scene,
      ...(llmAnalysis.visible_findings || []).slice(0, 5),
    ].filter(Boolean).slice(0, 8)

    imageTagsText.value = tags.join('、')
    imageSummary.value = buildImageSummary(data) || '图片已完成基础识别，请结合文字描述继续提问。'
    imageStatus.value = '图片已识别，会随消息一起发送给 AI。'
    return true
  } catch (error) {
    imageStatus.value = '图片识别请求失败，请检查后端服务。'
    console.error(error)
    return false
  } finally {
    imageLoading.value = false
  }
}

const appendFollowup = async (item) => {
  question.value = question.value.trim()
    ? `${question.value.trim()}\n${item}`
    : item
  await nextTick()
  focusComposer()
  await resizeComposer()
}

const collapseHistoryOnCompactScreen = () => {
  if (window.matchMedia('(max-width: 760px)').matches) {
    sidePanelOpen.value = false
  }
}

const startNewConversation = async () => {
  if (loading.value) return

  collapseHistoryOnCompactScreen()
  clearCurrentConversation()
  question.value = ''
  clearAttachment()
  stopSpeaking()
  if (route.query.session_id) {
    await router.replace({ path: '/chat' })
  }
  focusComposer()
  await resizeComposer()
}

const openConversationSession = (sessionId) => {
  if (!sessionId || loading.value) return
  collapseHistoryOnCompactScreen()
  router.push({
    path: '/chat',
    query: {
      session_id: sessionId,
    },
  })
}

const buildUserText = (payload) => {
  const parts = []
  if (payload.text.trim()) parts.push(payload.text.trim())
  if (payload.image_summary?.trim()) {
    parts.push(imageFileName.value ? `已添加图片：${imageFileName.value}` : '已添加图片')
  } else if (imageFileName.value && imageStatus.value) {
    parts.push(`已上传图片：${imageFileName.value}（${imageStatus.value}）`)
  } else if (imagePreview.value) {
    parts.push('已上传图片')
  }
  return parts.join('\n')
}

const getPayloadInputType = (payload) => {
  if (payload.text && payload.image_summary) return 'mixed'
  if (payload.image_summary) return 'image'
  return 'text'
}

const buildConversationHistory = () => messages.value
  .filter((message) => message.type !== 'loading' && message.content)
  .slice(-6)
  .map((message) => ({
    role: message.role,
    content: message.content,
    action: message.action || '',
    intent: message.intent || '',
    current_topic: message.trace?.planner?.current_topic || message.docs?.[0]?.title || '',
    docs: (message.docs || []).slice(0, 3).map((doc) => ({
      title: doc.title || '',
      doc_type: doc.doc_type || '',
    })),
  }))

const submitQuestion = async () => {
  if (!canSubmit.value || loading.value) return

  const pendingInputType = inputType.value
  const pendingText = question.value.trim()
  const hasPendingImage = Boolean(imagePreview.value || imageFileRef.value || imageFileName.value)
  const effectiveText = pendingText || (hasPendingImage ? '请根据我上传的图片进行健康分析' : '')
  if (hasPendingImage && !imagePreview.value && imageFileRef.value) {
    imageStatus.value = '正在读取图片...'
    try {
      imagePreview.value = await prepareImagePreview(imageFileRef.value)
      imageStatus.value = '图片已添加，发送后会和文字一起分析。'
    } catch (error) {
      console.error(error)
      imageStatus.value = '图片读取失败，请重新选择图片。'
      return
    }
  }

  if (hasPendingImage && !imagePreview.value) {
    imageStatus.value = pendingText
      ? '图片读取失败，请重新选择图片，或移除附件后发送文字。'
      : '图片读取失败，请重新选择图片。'
    return
  }

  const pendingImagePreview = imagePreview.value
  const pendingImageFileName = imageFileName.value
  const previousHistory = buildConversationHistory()
  const initialPayload = {
    input_type: pendingInputType,
    text: pendingText,
    image_summary: imageSummary.value.trim(),
    image_tags: parseImageTags(),
  }
  const userContent = buildUserText(initialPayload)

  messages.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content: userContent,
  })

  const loadingId = `loading-${Date.now()}`
  messages.value.push({
    id: loadingId,
    role: 'assistant',
    type: 'loading',
    hasImageAnalysis: Boolean(pendingImagePreview && !imageSummary.value.trim()),
    loadingStage: pendingImagePreview && !imageSummary.value.trim() ? 'image' : 'safety',
    content: '',
  })

  question.value = ''
  loading.value = true
  scheduleLoadingStages(loadingId, Boolean(pendingImagePreview && !imageSummary.value.trim()))
  await resizeComposer()
  await scrollToBottom()

  try {
    if (pendingImagePreview && !imageSummary.value && !imageLoading.value) {
      const imageOk = await analyzeImageForChat(effectiveText)
      if (!imageOk) {
        throw new Error(imageStatus.value || '图片识别失败，请稍后重试。')
      }
    }

    if (pendingImagePreview && !imageSummary.value.trim()) {
      throw new Error(`图片识别没有返回有效结果：${pendingImageFileName || '未命名图片'}`)
    }

    const payload = {
      input_type: pendingInputType,
      text: effectiveText,
      image_summary: imageSummary.value.trim(),
      image_tags: parseImageTags(),
      history: previousHistory,
      session_id: activeSessionId.value,
    }
    payload.text = effectiveText
    payload.input_type = getPayloadInputType(payload)
    clearAttachment()

    const response = await fetch(apiUrl('/api/agent/chat'), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(payload),
    })

    const data = await response.json()
    if (data.session_id) {
      activeSessionId.value = data.session_id
    }
    const loadingIndex = messages.value.findIndex((item) => item.id === loadingId)
    const assistantMessage = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: data.answer || '暂时没有生成回答，请稍后再试。',
      warning: data.warning || null,
      followups: data.followup_questions || [],
      docs: data.retrieved_docs || [],
      trace: data.agent_trace || null,
      action: data.action || '',
      intent: data.intent || data.agent_trace?.intent || '',
      confidence: data.confidence ?? data.agent_trace?.confidence ?? null,
      reliability: data.reliability || data.agent_trace?.reliability || null,
      llm: data.llm || null,
      error: data.error || null,
      historyId: data.history_id || null,
      feedbackType: '',
      feedbackStatus: '',
      feedbackLoading: false,
    }

    if (loadingIndex >= 0) {
      messages.value.splice(loadingIndex, 1, assistantMessage)
    } else {
      messages.value.push(assistantMessage)
    }
    saveChatCache()
    invalidateHistoryCaches()
    await loadConversationSessions()
  } catch (error) {
    const loadingIndex = messages.value.findIndex((item) => item.id === loadingId)
    const errorMessage = {
      id: `assistant-error-${Date.now()}`,
      role: 'assistant',
      content: error?.message || '请求失败，请检查后端服务是否正常运行。',
      error: {
        type: 'RequestError',
        message: error?.message || '请求失败',
      },
    }

    if (loadingIndex >= 0) {
      messages.value.splice(loadingIndex, 1, errorMessage)
    } else {
      messages.value.push(errorMessage)
    }
    console.error(error)
  } finally {
    clearLoadingStageTimers()
    loading.value = false
    await scrollToBottom()
  }
}

const triggerQuickConsult = (text) => {
  question.value = text
  submitQuestion()
}

const syncCurrentUser = () => {
  loadCurrentUser()
  loadConversationSessions()
}

onMounted(() => {
  sidePanelOpen.value = window.matchMedia('(min-width: 761px)').matches
  syncCurrentUser()
  refreshSpeechSupport()
  speechSynthesisSupported.value = 'speechSynthesis' in window
  window.addEventListener('storage', syncCurrentUser)
  window.addEventListener('rag-user-change', syncCurrentUser)
  const sessionId = route.query.session_id
  if (sessionId) {
    restoreSessionFromServer(sessionId)
  } else {
    restoreChatCache()
  }

  // Handle pending question redirected from the HomeView symptom search bar
  const pendingQuestion = sessionStorage.getItem('home_pending_question')
  if (pendingQuestion) {
    sessionStorage.removeItem('home_pending_question')
    question.value = pendingQuestion
    nextTick(() => {
      submitQuestion()
    })
  }
})

watch(
  () => route.query.session_id,
  (sessionId, oldSessionId) => {
    if (sessionId && sessionId !== oldSessionId) {
      restoreSessionFromServer(sessionId)
    }
    if (!sessionId && oldSessionId) {
      restoreChatCache()
    }
  },
)

onBeforeUnmount(() => {
  saveChatCache()
  clearLoadingStageTimers()
  stopRecognition()
  stopSpeaking()
  window.removeEventListener('storage', syncCurrentUser)
  window.removeEventListener('rag-user-change', syncCurrentUser)
})
</script>

<style scoped>
.chat-page {
  display: grid;
  gap: 18px;
}

.chat-shell {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: 0;
  height: calc(100dvh - 156px);
  min-height: 600px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.chat-side,
.chat-main {
  min-width: 0;
}

.chat-side {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 24px;
  background: var(--surface);
  border-right: 1px solid var(--outline-variant);
}

.side-primary-actions {
  flex: 0 0 auto;
}

.new-session-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 56px;
  width: 100%;
  min-width: 0;
  padding: 0 16px;
  color: #ffffff;
  background: var(--primary-bright);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 18px;
  font-weight: 800;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.new-session-btn:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.new-session-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.side-toggle {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  width: 100%;
  min-height: 48px;
  margin-top: 16px;
  padding: 0 4px;
  color: var(--text-secondary);
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 9px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 800;
  transition: 0.2s ease;
}

.side-toggle:hover,
.side-toggle[aria-expanded='true'] {
  color: var(--text-primary);
  background: rgba(226, 232, 240, 0.72);
}

.side-toggle svg {
  transition: transform 0.2s ease;
}

.side-toggle svg.open {
  transform: rotate(180deg);
}

.side-toggle small {
  display: grid;
  min-width: 23px;
  height: 23px;
  margin-left: auto;
  padding: 0 6px;
  place-items: center;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.9);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.side-content {
  display: none;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.side-content.open {
  display: flex;
  flex-direction: column;
  animation: historyFoldDown 0.2s ease-out;
}

@keyframes historyFoldDown {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.session-panel {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 0 0;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.section-title {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.section-title strong {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 800;
}

.section-title > div {
  display: flex;
  align-items: center;
  gap: 7px;
}

.section-title > div span {
  display: grid;
  min-width: 23px;
  height: 23px;
  padding: 0 6px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 900;
}

.section-title button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 0 10px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.section-title button:hover:not(:disabled) {
  color: var(--primary);
  background: var(--primary-soft);
  border-color: #93c5fd;
}

.session-search {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 54px;
  margin-bottom: 14px;
  padding: 0 14px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  transition: 0.2s ease;
}

.session-search:focus-within {
  color: var(--primary);
  background: #fff;
  border-color: #bfdbfe;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.session-search input {
  width: 100%;
  min-width: 0;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: 0;
  font-size: 16px;
}

.session-search button {
  display: grid;
  width: 23px;
  height: 23px;
  flex: 0 0 auto;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
}

.session-search button:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.session-empty,
.session-status {
  padding: 12px;
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-muted);
  text-align: center;
}

.session-list {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  padding-right: 2px;
}

.session-list button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 8px;
  align-items: center;
  width: 100%;
  min-height: 68px;
  padding: 12px 14px;
  color: var(--text-secondary);
  text-align: left;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-list button:hover,
.session-list button.active {
  color: var(--primary);
  background: var(--primary-soft);
  border-color: #93c5fd;
}

.session-list button.active {
  box-shadow: inset 3px 0 0 var(--primary);
}

.session-list svg {
  grid-row: span 2;
  color: var(--text-muted);
}

.session-list button.active svg {
  color: var(--primary);
}

.session-list span {
  font-weight: 800;
  font-size: 17px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-list small {
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 600;
}

.chat-main {
  display: grid;
  grid-template-rows: 80px minmax(0, 1fr) auto auto;
  min-height: 0;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.94);
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--outline-variant);
}

.assistant-identity {
  display: flex;
  align-items: center;
  gap: 14px;
}

.assistant-icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  color: var(--primary);
  background: #dae8ff;
  border-radius: var(--radius-lg);
}

.assistant-identity strong,
.assistant-identity small {
  display: flex;
  align-items: center;
}

.assistant-identity strong {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 850;
  line-height: 1.25;
}

.assistant-identity small {
  gap: 8px;
  margin-top: 4px;
  color: var(--teal-bright);
  font-size: 14px;
  font-weight: 650;
}

.assistant-identity small i {
  width: 10px;
  height: 10px;
  background: var(--teal-bright);
  border-radius: 50%;
  animation: statusPulse 1.7s ease-in-out infinite;
}

@keyframes statusPulse {
  50% { opacity: 0.45; }
}

.chat-menu-button {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
}

.chat-menu-button:hover {
  color: var(--text-primary);
  background: var(--surface-container);
}

.conversation {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding: 28px clamp(22px, 3vw, 40px);
  scroll-behavior: smooth;
  background:
    radial-gradient(circle at 92% 4%, rgba(0, 191, 165, 0.035), transparent 28%),
    var(--surface);
}

/* Empty consultation state styles */
.empty-conversation-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin: auto 0;
  max-width: 740px;
  align-self: center;
  text-align: center;
  padding: 40px 20px;
}

.empty-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  color: var(--primary);
  background: var(--primary-soft);
  margin-bottom: 20px;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.1);
}

.med-cross-icon {
  width: 32px;
  height: 32px;
}

.empty-conversation-state h2 {
  font-size: 30px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.empty-subtitle {
  font-size: 18px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 32px;
  max-width: 580px;
}

.quick-prompts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  width: 100%;
}

.quick-prompt-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--shadow-sm);
}

.quick-prompt-card:hover {
  border-color: var(--primary);
  background: var(--primary-soft);
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
}

.prompt-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.quick-prompt-card:hover .prompt-title {
  color: var(--primary);
}

.prompt-desc {
  font-size: 15px;
  color: var(--text-muted);
  line-height: 1.5;
}

.safety-note {
  padding: 12px 18px;
  color: var(--warning-text);
  background: var(--warning-soft);
  border-top: 1px solid var(--warning-border);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .chat-shell {
    grid-template-columns: minmax(230px, 260px) minmax(0, 1fr);
    height: calc(100dvh - 220px);
    min-height: 420px;
    overflow: hidden;
  }
}

@media (max-width: 760px) {
  .chat-page {
    min-height: 0;
    margin: 0;
  }

  .chat-shell {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: calc(100dvh - 176px);
    min-height: 540px;
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
  }

  .chat-side {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    flex: 0 0 auto;
    gap: 8px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.96);
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .new-session-btn {
    min-height: 48px;
    min-width: 0;
    font-size: 15px;
  }

  .side-toggle {
    min-height: 48px;
    margin-top: 0;
    padding: 0 10px;
    background: var(--surface-soft);
    border: 1px solid var(--border);
    font-size: 15px;
  }

  .side-content {
    grid-column: 1 / -1;
  }

  .side-content.open {
    max-height: 30dvh;
  }

  .session-list {
    max-height: 160px;
  }

  .chat-main {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .chat-header {
    order: 0;
    min-height: 68px;
    padding: 0 14px;
  }

  .assistant-icon {
    width: 42px;
    height: 42px;
  }

  .assistant-identity strong {
    font-size: 17px;
  }

  .conversation {
    order: 1;
    flex: 1 1 auto;
    min-height: 0;
    padding: 14px;
  }

  .quick-prompts-grid {
    grid-template-columns: 1fr;
  }

  .safety-note {
    order: 2;
    padding: 8px 12px;
    font-size: 12px;
  }

  :deep(.composer-container) {
    position: sticky;
    bottom: 0;
    z-index: 6;
    order: 3;
    padding: 10px 10px calc(10px + env(safe-area-inset-bottom));
  }
}
</style>
