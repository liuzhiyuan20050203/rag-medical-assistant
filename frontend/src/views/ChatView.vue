<template>
  <div class="chat-page">
    <section class="chat-shell">
      <aside class="chat-side">
        <div class="assistant-card">
          <span class="assistant-badge">AI 医疗 Agent</span>
          <h2>把症状、药品和图片都发到这里</h2>
          <p>
            系统会统一处理文字、语音和图片线索，优先识别危险信号，再检索知识库生成参考建议。
          </p>
        </div>

        <div class="quick-panel">
          <div class="section-title">
            <strong>咨询提示</strong>
            <span>描述越清楚越好</span>
          </div>
          <article
            v-for="item in consultationTips"
            :key="item.label"
            class="quick-card"
          >
            <strong>{{ item.label }}</strong>
            <span>{{ item.hint }}</span>
          </article>
        </div>

        <div v-if="isAdmin" class="admin-tip">
          <strong>管理员模式</strong>
          <span>可查看 Agent 调度、可靠性评分和工具调用链路。</span>
        </div>
      </aside>

      <main class="chat-main">
        <div ref="conversationRef" class="conversation">
          <article class="message assistant-message">
            <div class="avatar">AI</div>
            <div class="bubble">
              <strong>你好，我是 AI 医疗 Agent，可以帮你梳理症状和用药问题。</strong>
              <p>
                你可以直接描述症状、询问药品禁忌，或上传药盒、症状照片、检查单图片。
              </p>
            </div>
          </article>

          <article
            v-for="message in messages"
            :key="message.id"
            :class="['message', `${message.role}-message`]"
          >
            <div class="avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
            <div class="bubble">
              <div v-if="message.type === 'loading'" class="typing">
                <span></span>
                <span></span>
                <span></span>
                正在分析你的描述...
              </div>

              <template v-else>
                <pre>{{ message.content }}</pre>

                <div v-if="message.role === 'assistant'" class="message-actions">
                  <span v-if="message.llm" :class="['llm-badge', message.llm.used ? 'llm-on' : 'llm-off']">
                    {{ message.llm.used ? `AI 大模型参与：${message.llm.model || message.llm.provider || '已启用'}` : '本地知识库模板回答' }}
                  </span>
                  <button
                    v-if="speechSynthesisSupported"
                    type="button"
                    @click="toggleSpeak(message)"
                  >
                    {{ speakingMessageId === message.id ? '停止朗读' : '朗读回答' }}
                  </button>
                </div>

                <div v-if="message.role === 'assistant' && message.historyId" class="feedback-panel">
                  <span>{{ message.feedbackStatus || '这次回答有帮助吗？' }}</span>
                  <div class="feedback-actions">
                    <button
                      v-for="item in feedbackOptions"
                      :key="item.label"
                      type="button"
                      :class="{ active: message.feedbackType === item.label }"
                      :disabled="message.feedbackLoading"
                      @click="submitFeedback(message, item)"
                    >
                      {{ item.label }}
                    </button>
                  </div>
                </div>

                <div v-if="message.warning?.has_warning" class="inline-warning">
                  <strong>需要优先注意</strong>
                  <p>{{ message.warning.message }}</p>
                  <div class="tag-list">
                    <span v-for="item in message.warning.matched" :key="item">{{ item }}</span>
                  </div>
                </div>

                <div v-if="message.role === 'assistant' && message.reliability" :class="['reliability-note', reliabilityClass(message.reliability)]">
                  <strong>{{ message.reliability.label || reliabilityLevelLabel(message.reliability.level) }}</strong>
                  <p>{{ message.reliability.message }}</p>
                </div>

                <div v-if="message.followups?.length" class="followup-list">
                  <button
                    v-for="item in message.followups"
                    :key="item"
                    type="button"
                    @click="appendFollowup(item)"
                  >
                    {{ item }}
                  </button>
                </div>

                <div v-if="message.docs?.length" class="source-list">
                  <details>
                    <summary>查看参考知识来源 {{ message.docs.length }} 条</summary>
                    <div v-for="(doc, index) in message.docs" :key="index" class="source-card">
                      <strong>{{ index + 1 }}. {{ doc.title || '知识片段' }}</strong>
                      <span>{{ doc.doc_type === 'medicine' ? '药品' : '常见病' }}</span>
                      <p>{{ doc.content }}</p>
                    </div>
                  </details>
                </div>

                <div v-if="isAdmin && message.trace" class="agent-panel">
                  <div class="agent-header">
                    <strong>Agent 调度</strong>
                    <span>{{ labelAction(message.action) }}</span>
                  </div>
                  <p class="agent-decision">{{ agentDecisionSummary(message) }}</p>
                  <div class="agent-metrics">
                    <div>
                      <small>意图</small>
                      <b>{{ labelIntent(message.intent) }}</b>
                    </div>
                    <div>
                      <small>综合可靠性</small>
                      <b>{{ formatConfidence(message.reliability?.final_score ?? message.confidence) }}</b>
                    </div>
                    <div v-if="message.reliability">
                      <small>安全风险</small>
                      <b>{{ safetyLevelLabels[message.reliability.safety_level] || message.reliability.safety_level }}</b>
                    </div>
                  </div>
                  <div v-if="message.reliability?.components" class="reliability-breakdown">
                    <div v-for="item in reliabilityComponents(message.reliability)" :key="item.key">
                      <span>{{ item.label }}</span>
                      <b>{{ formatConfidence(item.value) }}</b>
                    </div>
                  </div>
                  <p v-if="message.reliability?.method" class="reliability-method">
                    {{ message.reliability.method }}
                  </p>
                  <p>{{ message.trace.summary || message.trace.reason }}</p>
                  <div class="tool-list">
                    <span v-for="tool in message.trace.used_tools" :key="tool">{{ labelTool(tool) }}</span>
                  </div>
                </div>

                <div v-if="isAdmin && message.error" class="error-box">
                  <strong>Agent 处理异常</strong>
                  <p>{{ message.error.message }}</p>
                  <span>{{ message.error.type }}</span>
                </div>
              </template>
            </div>
          </article>
        </div>

        <form class="composer" @submit.prevent="submitQuestion">
          <div v-if="attachmentVisible || speechStatusText" class="composer-status">
            <div v-if="attachmentVisible" class="attachment-pill">
              <img v-if="imagePreview" :src="imagePreview" alt="已添加的图片" />
              <Paperclip v-else :size="18" aria-hidden="true" />
              <span>{{ attachmentLabel }}</span>
              <b v-if="imageLoading">处理中</b>
              <button type="button" title="移除附件" aria-label="移除附件" @click="clearAttachment">
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
              @click="toggleVoiceInput"
            >
              <MicOff v-if="isListening" :size="22" aria-hidden="true" />
              <Mic v-else :size="22" aria-hidden="true" />
            </button>

            <textarea
              ref="textareaRef"
              v-model="question"
              :placeholder="mainPlaceholder"
              rows="1"
              @input="resizeComposer"
              @keydown.enter.exact.prevent="submitQuestion"
            ></textarea>

            <input
              ref="imageInputRef"
              type="file"
              accept="image/*"
              class="sr-only"
              @change="handleImageFile"
            />
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*,.pdf,.doc,.docx,.txt"
              class="sr-only"
              @change="handleLocalFile"
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
            </button>

            <button
              type="button"
              class="icon-btn"
              title="添加本地文件"
              aria-label="添加本地文件"
              :disabled="loading || imageLoading"
              @click="openFilePicker"
            >
              <FolderOpen :size="22" aria-hidden="true" />
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
            </button>
          </div>

          <button type="button" class="clear-chat-btn" @click="clearConversation" :disabled="loading">
            <Trash2 :size="16" aria-hidden="true" />
            清空对话
          </button>
        </form>

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
  FolderOpen,
  Image,
  LoaderCircle,
  Mic,
  MicOff,
  Paperclip,
  Send,
  Trash2,
  X,
} from '@lucide/vue'
import { apiUrl } from '../api'

const route = useRoute()
const router = useRouter()

const consultationTips = [
  {
    label: '症状描述',
    hint: '说清楚部位、持续时间、是否加重。',
  },
  {
    label: '危险信号',
    hint: '胸痛、呼吸困难、高热不退要优先说明。',
  },
  {
    label: '用药核对',
    hint: '可以直接问药品禁忌、剂量和注意事项。',
  },
  {
    label: '图片辅助',
    hint: '药盒、症状照片、检查单可作为参考线索。',
  },
]

const feedbackOptions = [
  { label: '有帮助', rating: 5, text: '有帮助' },
  { label: '不准确', rating: 1, text: '回答不准确' },
  { label: '太慢', rating: 2, text: '响应速度太慢' },
  { label: '没看懂图片', rating: 1, text: '图片识别或图片理解不准确' },
  { label: '答非所问', rating: 1, text: '回答和问题不匹配' },
]

const actionLabels = {
  danger_alert: '危险症状提醒',
  ask_followup: '追问关键信息',
  rag_answer: '症状知识库问答',
  medicine_query: '药品知识库查询',
  image_assist: '图片线索辅助分析',
  empty_input: '等待补充输入',
  agent_error: 'Agent 调度异常',
}

const intentLabels = {
  unknown: '未知输入',
  danger_alert: '疑似危险症状',
  followup: '信息不足需要追问',
  medicine_query: '药品用药咨询',
  image_assist: '图片相关健康咨询',
  symptom_query: '常见症状咨询',
  symptom_image: '症状图片咨询',
  general_health: '一般健康咨询',
}

const toolLabels = {
  normalize_input: '整理文字/语音/图片输入',
  warning_check: '危险症状规则检查',
  rule_planner: '规则意图判断',
  llm_planner: '大模型意图规划',
  medicine_search: '药品知识库查询',
  rag_search: 'RAG 知识库检索',
  llm_answer: '大模型生成回答',
  local_fallback: '本地模板兜底回答',
  agent_chat: 'Agent 统一调度入口',
}

const reliabilityLabels = {
  high: '资料匹配充分',
  medium: '资料匹配一般',
  low: '依据偏弱',
  insufficient: '依据不足',
}

const reliabilityComponentLabels = {
  knowledge_match: '知识库匹配',
  faithfulness: '回答支撑度',
  answer_relevance: '问题相关度',
  input_completeness: '输入完整度',
  consistency: '多轮一致性',
  source_authority: '来源权威度',
}

const safetyLevelLabels = {
  high: '高',
  medium: '中',
  low: '低',
}

const inputType = ref('text')
const question = ref('')
const imageSummary = ref('')
const imageTagsText = ref('')
const imagePreview = ref('')
const imageFileName = ref('')
const imageFileRef = ref(null)
const imageLoading = ref(false)
const imageStatus = ref('')
const messages = ref([])
const loading = ref(false)
const currentUser = ref(null)
const activeSessionId = ref(null)
const conversationRef = ref(null)
const textareaRef = ref(null)
const imageInputRef = ref(null)
const fileInputRef = ref(null)
const recognition = ref(null)
const isListening = ref(false)
const speechStatus = ref('')
const speakingMessageId = ref('')
const restoringSession = ref(false)
const restoreStatus = ref('')

const getSpeechRecognition = () => window.SpeechRecognition || window.webkitSpeechRecognition
const speechRecognitionSupported = ref(false)
const speechSynthesisSupported = ref(false)

const canSubmit = computed(() => {
  return Boolean(
    question.value.trim()
    || imagePreview.value
    || imageFileRef.value
    || imageSummary.value.trim()
    || imageTagsText.value.trim()
  )
})

const isAdmin = computed(() => currentUser.value?.role === 'admin')

const attachmentVisible = computed(() => Boolean(imagePreview.value || imageFileName.value || imageStatus.value))

const attachmentLabel = computed(() => {
  if (imageLoading.value) return imageFileName.value ? `正在识别 ${imageFileName.value}` : '正在识别图片'
  if (imageFileName.value && !imagePreview.value && !imageFileRef.value) return `图片未读取成功，请重新选择 ${imageFileName.value}`
  if (imageStatus.value && !imagePreview.value && !imageFileRef.value) return imageStatus.value
  if (imageSummary.value || imageTagsText.value) return imageFileName.value ? `已添加 ${imageFileName.value}` : '已添加图片'
  if (imageFileName.value) return `已选择 ${imageFileName.value}`
  return '已添加附件'
})

const mainPlaceholder = computed(() => '发消息或按住说话，可以添加药盒、检查单、症状照片...')

const speechStatusText = computed(() => {
  if (!speechRecognitionSupported.value) return '当前浏览器不支持语音识别，建议使用 Chrome 或 Edge。'
  if (speechStatus.value) return speechStatus.value
  if (restoreStatus.value) return restoreStatus.value
  return ''
})

const labelAction = (action) => actionLabels[action] || action || '未判断'

const labelIntent = (intent) => intentLabels[intent] || intent || '未识别'

const labelTool = (tool) => toolLabels[tool] || tool

const agentDecisionSummary = (message) => {
  const action = labelAction(message.action)
  const intent = labelIntent(message.intent)
  const tools = (message.trace?.used_tools || []).map(labelTool)

  if (message.action === 'danger_alert') {
    return 'Agent 决策：识别到可能的危险症状，优先触发安全提醒，并跳过普通咨询流程。'
  }

  if (message.action === 'medicine_query') {
    return 'Agent 决策：识别为药品或用药问题，优先调用药品知识库，再组织安全回答。'
  }

  if (message.action === 'ask_followup') {
    return 'Agent 决策：当前信息不足，先追问关键症状、持续时间或特殊人群信息。'
  }

  if (message.action === 'rag_answer') {
    return 'Agent 决策：识别为常见症状咨询，调用 RAG 知识库检索相关依据后生成回答。'
  }

  if (message.action === 'image_assist') {
    return 'Agent 决策：将图片识别结果作为辅助线索，并结合文字描述和知识库进行判断。'
  }

  return `Agent 决策：识别意图为“${intent}”，执行“${action}”${tools.length ? `，调用了${tools.join('、')}` : ''}。`
}

const chatCacheKey = computed(() => {
  const userKey = currentUser.value?.id || currentUser.value?.username || 'guest'
  return `rag-chat-current:${userKey}`
})

const loadCurrentUser = () => {
  const raw = localStorage.getItem('ragUser')
  currentUser.value = raw ? JSON.parse(raw) : null
}

const saveChatCache = () => {
  const cache = {
    activeSessionId: activeSessionId.value,
    messages: messages.value.filter((message) => message.type !== 'loading'),
    savedAt: Date.now(),
  }
  sessionStorage.setItem(chatCacheKey.value, JSON.stringify(cache))
}

const clearChatCache = () => {
  sessionStorage.removeItem(chatCacheKey.value)
}

const restoreChatCache = async () => {
  const raw = sessionStorage.getItem(chatCacheKey.value)
  if (!raw) return false

  try {
    const cache = JSON.parse(raw)
    activeSessionId.value = cache.activeSessionId || null
    messages.value = Array.isArray(cache.messages) ? cache.messages : []
    await scrollToBottom()
    return messages.value.length > 0
  } catch (error) {
    clearChatCache()
    console.error(error)
    return false
  }
}

const mapStoredMessage = (message) => {
  if (message.role === 'user') {
    return {
      id: `stored-user-${message.id}`,
      role: 'user',
      content: message.content || '',
    }
  }

  return {
    id: `stored-assistant-${message.id}`,
    role: 'assistant',
    content: message.content || '',
    warning: message.warning || message.trace?.warning || null,
    followups: message.followup_questions || [],
    docs: message.retrieved_docs || [],
    trace: message.trace || null,
    action: message.action || '',
    intent: message.intent || message.trace?.intent || '',
    confidence: message.confidence ?? message.trace?.confidence ?? null,
    reliability: message.reliability || message.trace?.reliability || null,
    error: null,
    historyId: message.history_id || null,
    feedbackType: '',
    feedbackStatus: '',
    feedbackLoading: false,
  }
}

const restoreSessionFromServer = async (sessionId) => {
  if (!sessionId || restoringSession.value) return

  restoringSession.value = true
  restoreStatus.value = '正在恢复历史会话...'

  try {
    const response = await fetch(apiUrl(`/api/conversations/${sessionId}`), {
      headers: authHeaders(),
    })
    const data = await response.json()

    if (!response.ok || !data.success) {
      restoreStatus.value = data.message || '历史会话恢复失败。'
      return
    }

    const detail = data.data || {}
    activeSessionId.value = detail.id || Number(sessionId)
    messages.value = (detail.messages || []).map(mapStoredMessage).filter((item) => item.content)
    saveChatCache()
    restoreStatus.value = `已恢复历史会话 #${activeSessionId.value}`
    await scrollToBottom()
  } catch (error) {
    restoreStatus.value = '历史会话恢复失败，请检查后端服务。'
    console.error(error)
  } finally {
    restoringSession.value = false
  }
}

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

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

const formatConfidence = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '暂无'
  }

  return `${Math.round(Number(value) * 100)}%`
}

const reliabilityLevelLabel = (level) => reliabilityLabels[level] || '待评估'

const reliabilityClass = (reliability) => `reliability-${reliability?.level || 'unknown'}`

const reliabilityComponents = (reliability) => Object.entries(reliability?.components || {})
  .map(([key, value]) => ({
    key,
    label: reliabilityComponentLabels[key] || key,
    value,
  }))

const resizeComposer = async () => {
  await nextTick()
  const textarea = textareaRef.value
  if (!textarea) return

  textarea.style.height = 'auto'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`
}

const setupRecognition = () => {
  const SpeechRecognition = getSpeechRecognition()
  if (!SpeechRecognition || recognition.value) return

  const instance = new SpeechRecognition()
  instance.lang = 'zh-CN'
  instance.continuous = true
  instance.interimResults = true

  let finalText = ''

  instance.onstart = () => {
    finalText = question.value.trim() ? `${question.value.trim()} ` : ''
    isListening.value = true
    speechStatus.value = '正在听，请自然说出你的症状。'
  }

  instance.onresult = (event) => {
    let interimText = ''
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index]
      const transcript = result[0]?.transcript || ''
      if (result.isFinal) {
        finalText += transcript
      } else {
        interimText += transcript
      }
    }

    const recognizedText = `${finalText}${interimText}`.trim()
    if (recognizedText) {
      question.value = recognizedText
      speechStatus.value = interimText ? '正在识别...' : '已识别，可继续说或点击停止。'
    }
  }

  instance.onerror = (event) => {
    isListening.value = false
    speechStatus.value = event.error === 'not-allowed'
      ? '麦克风权限被拒绝，请允许浏览器使用麦克风。'
      : `语音识别失败：${event.error || '未知错误'}`
  }

  instance.onend = () => {
    isListening.value = false
    if (!speechStatus.value.includes('失败') && !speechStatus.value.includes('拒绝')) {
      speechStatus.value = question.value.trim()
        ? '识别已结束，可以检查文字后发送。'
        : '识别已结束，未获取到清晰语音。'
    }
    finalText = question.value
  }

  recognition.value = instance
}

const toggleVoiceInput = () => {
  speechRecognitionSupported.value = Boolean(getSpeechRecognition())

  if (!speechRecognitionSupported.value) {
    speechStatus.value = '当前浏览器不支持语音识别，建议使用 Chrome 或 Edge。'
    return
  }

  setupRecognition()

  if (isListening.value) {
    recognition.value?.stop()
    return
  }

  speechStatus.value = ''
  recognition.value?.start()
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

const handleImageFile = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  clearAttachment()
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
  event.target.value = ''
}

const handleLocalFile = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  if (isImageFile(file)) {
    await handleImageFile(event)
    return
  }

  clearAttachment()
  imageStatus.value = '当前先支持图片识别，PDF、Word 等文件解析会放到后续步骤。'
  event.target.value = ''
}

const openImagePicker = () => {
  imageInputRef.value?.click()
}

const openFilePicker = () => {
  fileInputRef.value?.click()
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
  textareaRef.value?.focus()
}

const clearConversation = () => {
  messages.value = []
  activeSessionId.value = null
  restoreStatus.value = ''
  question.value = ''
  clearAttachment()
  clearChatCache()
  if (route.query.session_id) {
    router.replace({ path: '/chat' })
  }
  textareaRef.value?.focus()
  resizeComposer()
}

const buildUserText = (payload) => {
  const parts = []
  if (payload.text.trim()) parts.push(payload.text.trim())
  if (payload.image_summary?.trim()) {
    parts.push(imageFileName.value ? `已添加图片：${imageFileName.value}` : '已添加图片')
    parts.push(`图片识别结果：\n${payload.image_summary.trim()}`)
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
    content: '',
  })

  question.value = ''
  loading.value = true
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
    loading.value = false
    await scrollToBottom()
  }
}

onMounted(() => {
  loadCurrentUser()
  speechRecognitionSupported.value = Boolean(getSpeechRecognition())
  speechSynthesisSupported.value = 'speechSynthesis' in window
  window.addEventListener('storage', loadCurrentUser)
  window.addEventListener('rag-user-change', loadCurrentUser)
  const sessionId = route.query.session_id
  if (sessionId) {
    restoreSessionFromServer(sessionId)
  } else {
    restoreChatCache()
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
  recognition.value?.stop()
  stopSpeaking()
  window.removeEventListener('storage', loadCurrentUser)
  window.removeEventListener('rag-user-change', loadCurrentUser)
})
</script>

<style scoped>
.chat-page {
  display: grid;
  gap: 18px;
}

.chat-shell {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 18px;
  height: calc(100vh - 178px);
  min-height: 620px;
}

.chat-side,
.chat-main {
  min-width: 0;
}

.chat-side {
  display: grid;
  align-content: start;
  gap: 14px;
}

.assistant-card,
.quick-panel,
.admin-tip,
.chat-main,
.safety-note {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.assistant-card {
  padding: 18px;
}

.assistant-badge {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 5px 10px;
  color: #0f766e;
  background: #ccfbf1;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.assistant-card h2 {
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 21px;
  line-height: 1.25;
}

.assistant-card p,
.section-title span,
.admin-tip span,
.safety-note {
  color: var(--text-muted);
}

.quick-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}

.section-title strong {
  color: var(--text-primary);
}

.section-title span {
  font-size: 12px;
}

.quick-card {
  display: grid;
  gap: 3px;
  width: 100%;
  min-height: 66px;
  padding: 10px 12px;
  color: var(--text-primary);
  text-align: left;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: default;
}

.quick-card:hover {
  background: #f8fafc;
  border-color: var(--border);
}

.quick-card span {
  color: var(--text-muted);
  font-size: 13px;
}

.admin-tip {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-color: #c7d2fe;
  background: #eef2ff;
}

.admin-tip strong {
  color: #3730a3;
}

.chat-main {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto auto;
  min-height: 0;
  overflow: hidden;
}

.conversation {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding: 22px;
  scroll-behavior: smooth;
}

.message {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  max-width: 940px;
}

.user-message {
  align-self: flex-end;
  grid-template-columns: minmax(0, 1fr) 42px;
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
  width: 42px;
  height: 42px;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 8px;
  font-weight: 800;
}

.bubble {
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.bubble strong {
  display: block;
  margin-bottom: 6px;
}

.bubble p {
  margin: 0;
  line-height: 1.8;
}

pre {
  margin: 0;
  color: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.85;
}

.typing {
  display: inline-flex;
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

.inline-warning,
.error-box {
  margin-top: 14px;
  padding: 14px;
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
}

.inline-warning strong,
.error-box strong {
  margin-bottom: 4px;
}

.tag-list,
.tool-list {
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
  margin-top: 14px;
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

.reliability-note {
  display: grid;
  gap: 5px;
  margin-top: 14px;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.reliability-note strong {
  font-size: 14px;
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

.reliability-high strong {
  color: #0f766e;
}

.reliability-medium {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.reliability-medium strong {
  color: #1d4ed8;
}

.reliability-low,
.reliability-insufficient,
.reliability-unknown {
  background: #fff7ed;
  border-color: #fed7aa;
}

.reliability-low strong,
.reliability-insufficient strong,
.reliability-unknown strong {
  color: #c2410c;
}

.source-list {
  margin-top: 14px;
}

.message-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
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
  border-radius: 8px;
  border: 1px solid var(--border);
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
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.feedback-panel > span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 800;
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

.source-list summary {
  color: #1d4ed8;
  cursor: pointer;
  font-weight: 800;
}

.source-card {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding: 12px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.source-card span {
  width: fit-content;
  padding: 2px 8px;
  color: #ffffff;
  background: var(--pharmacy-teal);
  border-radius: 999px;
  font-size: 12px;
}

.agent-panel {
  display: grid;
  gap: 10px;
  margin-top: 14px;
  padding: 14px;
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px dashed #94a3b8;
  border-radius: 8px;
}

.agent-header,
.agent-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.agent-header span,
.tool-list span,
.error-box span {
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.agent-header span {
  color: #0f766e;
  background: #ccfbf1;
}

.agent-decision {
  margin: 0;
  padding: 10px 12px;
  color: #155e75;
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.6;
}

.agent-metrics div {
  display: grid;
  gap: 2px;
  min-width: 120px;
}

.agent-metrics small {
  color: var(--text-muted);
}

.reliability-breakdown {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.reliability-breakdown div {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-height: 34px;
  padding: 6px 8px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.reliability-breakdown span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.reliability-breakdown b {
  color: var(--text-primary);
  font-size: 13px;
}

.reliability-method {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.tool-list span {
  color: #4338ca;
  background: #eef2ff;
}

.error-box span {
  display: inline-block;
  margin-top: 8px;
  color: #7f1d1d;
  background: #fee2e2;
}

.composer {
  display: grid;
  gap: 12px;
  padding: 16px;
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
  grid-template-columns: 46px minmax(0, 1fr) 46px 46px 46px;
  gap: 8px;
  align-items: end;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

textarea,
input {
  width: 100%;
  padding: 13px 14px;
  color: var(--text-primary);
  background: #ffffff;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  outline: none;
}

textarea:focus,
input:focus {
  border-color: var(--medical-blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

textarea {
  min-height: 46px;
  max-height: 150px;
  padding: 12px 4px;
  resize: none;
  overflow-y: auto;
  background: transparent;
  border: 0;
  border-radius: 8px;
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
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
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
  transform: translateX(1px);
}

.send-btn:disabled,
.icon-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.send-btn svg {
  animation: none;
}

.send-btn:disabled svg {
  animation: spin 1s linear infinite;
}

.clear-chat-btn {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  background: transparent;
  border: 0;
  cursor: pointer;
  font-weight: 700;
}

.clear-chat-btn:hover:not(:disabled) {
  color: #991b1b;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.safety-note {
  padding: 10px 16px;
  color: #9a3412;
  background: #fff7ed;
  border-top: 1px solid #fed7aa;
  border-right: 0;
  border-bottom: 0;
  border-left: 0;
  border-radius: 0;
  border-color: #fed7aa;
  box-shadow: none;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .chat-shell {
    grid-template-columns: 1fr;
  }

  .chat-main {
    min-height: 640px;
  }
}

@media (max-width: 640px) {
  .conversation {
    padding: 16px;
  }

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

  .chat-composer-bar {
    grid-template-columns: 42px minmax(0, 1fr) 42px 42px 42px;
    padding: 8px;
  }

  .icon-btn {
    width: 42px;
    height: 42px;
  }
}
</style>
