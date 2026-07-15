<template>
  <div class="chat-page">
    <section class="chat-shell">
      <aside class="chat-side">
        <div class="assistant-card">
          <span class="assistant-badge">AI 医疗 Agent</span>
          <h2>今天想咨询什么？</h2>
          <p>
            可以描述症状、询问药品，或上传图片/视频。系统会先检查危险信号，再给出参考建议。
          </p>
          <button type="button" class="new-session-btn" :disabled="loading" @click="startNewConversation">
            <Plus :size="17" aria-hidden="true" />
            新对话
          </button>
        </div>

        <button type="button" class="side-toggle" @click="sidePanelOpen = !sidePanelOpen">
          <ChevronDown :class="{ open: sidePanelOpen }" :size="16" aria-hidden="true" />
          历史与提示
        </button>

        <div :class="['side-content', { open: sidePanelOpen }]">
          <div class="session-panel">
            <div class="section-title">
              <strong>历史会话</strong>
              <button type="button" :disabled="sessionsLoading" @click="loadConversationSessions">
                <RefreshCw :size="14" aria-hidden="true" />
                {{ sessionsLoading ? '刷新中' : '刷新' }}
              </button>
            </div>

            <div v-if="!currentUser" class="session-empty">
              {{ isGuest ? '游客模式可直接咨询，登录后可保存并继续历史会话。' : '登录后会自动保存历史会话，并可从这里继续对话。' }}
            </div>
            <div v-else-if="sessionsLoading" class="session-empty">
              正在加载历史会话...
            </div>
            <div v-else-if="conversationSessions.length === 0" class="session-empty">
              暂无历史会话，发送第一条消息后会自动保存。
            </div>
            <div v-else class="session-list">
              <button
                v-for="session in conversationSessions"
                :key="session.id"
                type="button"
                :class="{ active: Number(activeSessionId) === Number(session.id) }"
                @click="openConversationSession(session.id)"
              >
                <History :size="15" aria-hidden="true" />
                <span>{{ session.title || `会话 #${session.id}` }}</span>
                <small>{{ session.message_count || 0 }} 条消息</small>
              </button>
            </div>

            <p v-if="sessionsStatus && currentUser" class="session-status">{{ sessionsStatus }}</p>
          </div>

          <div class="quick-panel">
            <div class="section-title">
              <strong>咨询提示</strong>
              <span>按需补充</span>
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
        </div>
      </aside>

      <main class="chat-main">
        <div ref="conversationRef" class="conversation">
          <ChatMessage
            :message="welcomeMessage"
            :is-admin="isAdmin"
            :interactive="false"
          />

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
        </div>

        <section class="safety-note">
          <strong>安全提示：</strong>
          <span>
            仅供健康参考；胸痛、呼吸困难、高热不退、意识模糊等情况请及时就医。
            未登录咨询可能以匿名方式用于系统统计和质量改进，不与个人账号绑定，请勿输入姓名、手机号、身份证号等身份信息。
          </span>
        </section>

        <ChatComposer
          ref="composerRef"
          v-model="question"
          :attachment-visible="attachmentVisible"
          :image-preview="imagePreview"
          :attachment-kind="attachmentKind"
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
          @video-file="handleVideoFile"
          @clear-attachment="clearAttachment"
        />
        <video
          ref="videoRef"
          class="media-probe"
          :src="videoPreviewUrl"
          muted
          playsinline
          @loadedmetadata="syncVideoDuration"
        ></video>
        <canvas ref="videoCanvasRef" class="media-probe" aria-hidden="true"></canvas>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronDown, History, Plus, RefreshCw } from '@lucide/vue'
import { apiUrl, clearPageCacheByPrefix } from '../api'
import ChatComposer from '../components/chat/ChatComposer.vue'
import ChatMessage from '../components/chat/ChatMessage.vue'
import { useChatSession } from '../composables/useChatSession'
import { useSpeechInput } from '../composables/useSpeechInput'

const route = useRoute()
const router = useRouter()

const consultationTips = [
  {
    label: '说症状',
    hint: '部位、多久了、有没有加重。',
  },
  {
    label: '问药品',
    hint: '药名、禁忌、剂量、注意事项。',
  },
  {
    label: '传图片/视频',
    hint: '药盒、说明书、症状表面照片或视频。',
  },
]

const feedbackOptions = [
  { label: '有帮助', rating: 5, text: '有帮助' },
  { label: '不准确', rating: 1, text: '回答不准确' },
  { label: '太慢', rating: 2, text: '响应速度太慢' },
  { label: '没看懂图片', rating: 1, text: '图片识别或图片理解不准确' },
  { label: '答非所问', rating: 1, text: '回答和问题不匹配' },
]

const welcomeMessage = {
  id: 'welcome',
  role: 'assistant',
  title: '你好，我可以帮你梳理症状、用药和图片/视频线索。',
  content: '请直接说出哪里不舒服、持续多久，或者上传药盒、药品说明书、症状表面照片或视频。',
}

const inputType = ref('text')
const question = ref('')
const imageSummary = ref('')
const imageTagsText = ref('')
const imagePreview = ref('')
const imageFileName = ref('')
const imageFileRef = ref(null)
const attachmentKind = ref('image')
const videoFileRef = ref(null)
const videoPreviewUrl = ref('')
const videoDuration = ref(0)
const videoRef = ref(null)
const videoCanvasRef = ref(null)
const imageLoading = ref(false)
const imageStatus = ref('')
const loading = ref(false)
const conversationRef = ref(null)
const composerRef = ref(null)
const speechSynthesisSupported = ref(false)
const speakingMessageId = ref('')
const sidePanelOpen = ref(false)
const loadingStageTimers = []

const isPageReload = () => {
  const navigation = performance.getEntriesByType?.('navigation')?.[0]
  return navigation?.type === 'reload'
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
    || videoFileRef.value
    || imageSummary.value.trim()
    || imageTagsText.value.trim()
  )
})

const attachmentVisible = computed(() => Boolean(imagePreview.value || imageFileName.value || imageStatus.value || videoFileRef.value))

const attachmentLabel = computed(() => {
  if (imageLoading.value && attachmentKind.value === 'video') return imageFileName.value ? `正在识别视频 ${imageFileName.value}` : '正在识别视频'
  if (imageLoading.value) return imageFileName.value ? `正在识别 ${imageFileName.value}` : '正在识别图片'
  if (attachmentKind.value === 'video' && imageFileName.value) return `已选择视频 ${imageFileName.value}`
  if (imageFileName.value && !imagePreview.value && !imageFileRef.value) return `图片未读取成功，请重新选择 ${imageFileName.value}`
  if (imageStatus.value && !imagePreview.value && !imageFileRef.value) return imageStatus.value
  if (imageSummary.value || imageTagsText.value) return imageFileName.value ? `已添加 ${imageFileName.value}` : '已添加图片'
  if (imageFileName.value) return `已选择 ${imageFileName.value}`
  return '已添加附件'
})

const mainPlaceholder = computed(() => '请描述症状、药品问题，或上传图片/视频...')

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
  clearPageCacheByPrefix('profile:')
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

const isVideoFile = (file) => {
  const type = String(file?.type || '').toLowerCase()
  const name = String(file?.name || '').toLowerCase()
  return type.startsWith('video/') || /\.(mp4|webm|mov|m4v|avi|mkv)$/i.test(name)
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
  attachmentKind.value = 'image'
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

const handleVideoFile = async (file) => {
  if (!file) return

  clearAttachment()

  if (!isVideoFile(file)) {
    imageStatus.value = '请选择视频文件。'
    return
  }

  inputType.value = question.value.trim() ? 'mixed' : 'video'
  attachmentKind.value = 'video'
  imageFileName.value = file.name
  videoFileRef.value = file
  videoPreviewUrl.value = URL.createObjectURL(file)
  imageStatus.value = '视频已添加，发送后会抽取关键帧分析。'
}

const clearAttachment = () => {
  imageSummary.value = ''
  imageTagsText.value = ''
  imagePreview.value = ''
  imageFileName.value = ''
  imageFileRef.value = null
  videoFileRef.value = null
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
  }
  videoPreviewUrl.value = ''
  videoDuration.value = 0
  attachmentKind.value = 'image'
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

const syncVideoDuration = () => {
  videoDuration.value = videoRef.value?.duration || 0
}

const waitForVideoMetadata = () =>
  new Promise((resolve) => {
    const video = videoRef.value
    if (!video || Number.isFinite(video.duration)) {
      resolve()
      return
    }

    const timeout = window.setTimeout(() => {
      video.removeEventListener('loadedmetadata', onLoaded)
      resolve()
    }, 1500)
    const onLoaded = () => {
      window.clearTimeout(timeout)
      video.removeEventListener('loadedmetadata', onLoaded)
      syncVideoDuration()
      resolve()
    }
    video.addEventListener('loadedmetadata', onLoaded)
  })

const seekVideo = (timestamp) =>
  new Promise((resolve) => {
    const video = videoRef.value
    if (!video) {
      resolve()
      return
    }

    const timeout = window.setTimeout(() => {
      video.removeEventListener('seeked', onSeeked)
      resolve()
    }, 1400)
    const onSeeked = () => {
      window.clearTimeout(timeout)
      video.removeEventListener('seeked', onSeeked)
      resolve()
    }
    video.addEventListener('seeked', onSeeked)
    video.currentTime = Math.min(Math.max(timestamp, 0), Math.max((video.duration || 0) - 0.1, 0))
  })

const captureVideoFrame = async (timestamp) => {
  const video = videoRef.value
  const canvas = videoCanvasRef.value
  if (!video || !canvas) return null

  await seekVideo(timestamp)

  const width = video.videoWidth || 640
  const height = video.videoHeight || 360
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, width, height)

  return {
    timestamp,
    image: canvas.toDataURL('image/jpeg', 0.78),
  }
}

const extractVideoFramesForChat = async () => {
  const video = videoRef.value
  if (!video) return []

  await waitForVideoMetadata()
  const duration = video.duration || videoDuration.value || 0
  const times = duration > 2
    ? [0.1, duration * 0.25, duration * 0.5, duration * 0.75, Math.max(duration - 0.2, 0.1)]
    : [0.1]

  const frames = []
  for (const time of times) {
    const frame = await captureVideoFrame(time)
    if (frame) frames.push(frame)
  }
  return frames
}

const buildVideoSummary = (result) => {
  const lines = []
  const answer = result?.answer || {}
  const llmAnalysis = result?.llm?.analysis || {}

  if (llmAnalysis.summary) {
    lines.push(llmAnalysis.summary)
  } else if (answer.summary) {
    lines.push(answer.summary)
  } else if (answer.conclusion) {
    lines.push(answer.conclusion)
  }

  if (Array.isArray(llmAnalysis.visible_findings) && llmAnalysis.visible_findings.length) {
    lines.push(`关键帧可见信息：${llmAnalysis.visible_findings.slice(0, 6).join('；')}`)
  } else if (Array.isArray(answer.evidence) && answer.evidence.length) {
    lines.push(`关键帧依据：${answer.evidence.slice(0, 5).join('；')}`)
  }

  if (llmAnalysis.likely_scene) {
    lines.push(`可能场景：${llmAnalysis.likely_scene}`)
  }

  if (result?.summary?.weak_frame_count) {
    lines.push(`画面质量提示：有 ${result.summary.weak_frame_count} 个关键帧可能偏暗或模糊。`)
  }

  return lines.filter(Boolean).join('\n')
}

const analyzeVideoForChat = async (noteText = '') => {
  if (!videoFileRef.value || imageLoading.value) return false

  imageLoading.value = true
  imageStatus.value = '正在抽取视频关键帧...'

  try {
    const frames = await extractVideoFramesForChat()
    if (!frames.length) {
      imageStatus.value = '视频关键帧抽取失败，请换一个更清晰的视频。'
      return false
    }

    imageStatus.value = '正在识别视频关键帧...'
    const response = await fetch(apiUrl('/api/multimodal/video/analyze'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        frames,
        file_name: imageFileName.value,
        note: noteText || question.value,
        duration: videoDuration.value,
      }),
    })
    const data = await response.json()

    if (!response.ok || !data.success) {
      imageStatus.value = data.message || `视频识别失败，状态码：${response.status}`
      return false
    }

    const llmAnalysis = data.llm?.analysis || {}
    const tags = [
      ...(data.summary?.tags || []),
      llmAnalysis.likely_scene,
      ...(llmAnalysis.visible_findings || []).slice(0, 5),
    ].filter(Boolean).slice(0, 8)

    imageTagsText.value = tags.join('、')
    imageSummary.value = buildVideoSummary(data) || '视频已完成关键帧识别，请结合文字描述继续提问。'
    imageStatus.value = '视频已识别，会随消息一起发送给 AI。'
    return true
  } catch (error) {
    imageStatus.value = '视频识别请求失败，请检查后端服务。'
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

const startNewConversation = async () => {
  if (loading.value) return

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
  const mediaLabel = attachmentKind.value === 'video' ? '视频' : '图片'
  if (payload.image_summary?.trim()) {
    parts.push(imageFileName.value ? `已添加${mediaLabel}：${imageFileName.value}` : `已添加${mediaLabel}`)
  } else if (imageFileName.value && imageStatus.value) {
    parts.push(`已上传${mediaLabel}：${imageFileName.value}（${imageStatus.value}）`)
  } else if (imagePreview.value) {
    parts.push('已上传图片')
  } else if (videoFileRef.value) {
    parts.push('已上传视频')
  }
  return parts.join('\n')
}

const getPayloadInputType = (payload, fallbackInputType = 'text') => {
  if (payload.text && payload.image_summary) return 'mixed'
  if (payload.image_summary && fallbackInputType === 'video') return 'video'
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
  const hasPendingVideo = Boolean(videoFileRef.value)
  const effectiveText = pendingText || (hasPendingVideo ? '请根据我上传的视频进行健康分析' : hasPendingImage ? '请根据我上传的图片进行健康分析' : '')
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

  if (hasPendingImage && !hasPendingVideo && !imagePreview.value) {
    imageStatus.value = pendingText
      ? '图片读取失败，请重新选择图片，或移除附件后发送文字。'
      : '图片读取失败，请重新选择图片。'
    return
  }

  const pendingImagePreview = imagePreview.value
  const pendingVideoFile = videoFileRef.value
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
    hasImageAnalysis: Boolean((pendingImagePreview || pendingVideoFile) && !imageSummary.value.trim()),
    loadingStage: (pendingImagePreview || pendingVideoFile) && !imageSummary.value.trim() ? 'image' : 'safety',
    content: '',
  })

  question.value = ''
  loading.value = true
  scheduleLoadingStages(loadingId, Boolean((pendingImagePreview || pendingVideoFile) && !imageSummary.value.trim()))
  saveChatCache()
  await resizeComposer()
  await scrollToBottom()

  try {
    if (pendingImagePreview && !imageSummary.value && !imageLoading.value) {
      const imageOk = await analyzeImageForChat(effectiveText)
      if (!imageOk) {
        throw new Error(imageStatus.value || '图片识别失败，请稍后重试。')
      }
    }

    if (pendingVideoFile && !imageSummary.value && !imageLoading.value) {
      const videoOk = await analyzeVideoForChat(effectiveText)
      if (!videoOk) {
        throw new Error(imageStatus.value || '视频识别失败，请稍后重试。')
      }
    }

    if ((pendingImagePreview || pendingVideoFile) && !imageSummary.value.trim()) {
      throw new Error(`${pendingVideoFile ? '视频' : '图片'}识别没有返回有效结果：${pendingImageFileName || '未命名文件'}`)
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
    payload.input_type = pendingText
      ? getPayloadInputType(payload, pendingInputType)
      : (payload.image_summary ? pendingInputType : 'text')
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
    saveChatCache()
    await scrollToBottom()
  }
}

const syncCurrentUser = () => {
  loadCurrentUser()
  loadConversationSessions()
}

onMounted(() => {
  syncCurrentUser()
  refreshSpeechSupport()
  speechSynthesisSupported.value = 'speechSynthesis' in window
  window.addEventListener('storage', syncCurrentUser)
  window.addEventListener('rag-user-change', syncCurrentUser)
  const sessionId = route.query.session_id
  if (sessionId) {
    restoreSessionFromServer(sessionId)
  } else {
    restoreChatCache({ markInterruptedLoading: isPageReload() })
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
  if (videoPreviewUrl.value) {
    URL.revokeObjectURL(videoPreviewUrl.value)
  }
  window.removeEventListener('storage', syncCurrentUser)
  window.removeEventListener('rag-user-change', syncCurrentUser)
})
</script>

<style scoped>
.chat-page {
  display: grid;
  gap: 12px;
}

.media-probe {
  position: fixed;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.chat-shell {
  display: grid;
  grid-template-columns: minmax(196px, 224px) minmax(0, 1fr);
  gap: 12px;
  height: calc(100dvh - 142px);
  min-height: 620px;
}

.chat-side,
.chat-main {
  min-width: 0;
}

.chat-side {
  display: grid;
  align-content: start;
  gap: 8px;
}

.assistant-card,
.session-panel,
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
  display: grid;
  gap: 9px;
  padding: 14px;
  background:
    linear-gradient(135deg, #ffffff, #f8fbfd),
    var(--surface);
}

.assistant-badge {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 2px;
  padding: 5px 10px;
  color: #0f766e;
  background: #ccfbf1;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.assistant-card h2 {
  margin-bottom: 0;
  color: var(--text-primary);
  font-size: 17px;
  line-height: 1.25;
}

.assistant-card p {
  display: none;
}

.assistant-card p,
.section-title span,
.session-empty,
.session-status,
.admin-tip span,
.safety-note {
  color: var(--text-muted);
}

.new-session-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 40px;
  padding: 0 12px;
  color: #ffffff;
  background: var(--medical-blue);
  border: 1px solid var(--medical-blue);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
}

.new-session-btn:hover:not(:disabled) {
  background: var(--medical-blue-dark);
}

.new-session-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.side-toggle {
  display: none;
}

.side-content {
  display: grid;
  gap: 8px;
}

.session-panel {
  display: grid;
  gap: 9px;
  padding: 12px;
}

.quick-panel {
  display: grid;
  gap: 7px;
  padding: 12px;
  background: #fbfdff;
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

.section-title button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 0 8px;
  color: var(--text-muted);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.section-title button:hover:not(:disabled) {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.section-title button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.session-empty,
.session-status {
  padding: 10px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
}

.session-list {
  display: grid;
  gap: 6px;
  max-height: 300px;
  overflow: auto;
}

.session-list button {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 2px 7px;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 8px;
  color: var(--text-secondary);
  text-align: left;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
}

.session-list button:hover,
.session-list button.active {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #93c5fd;
}

.session-list svg {
  grid-row: span 2;
}

.session-list span,
.session-list small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-list span {
  font-weight: 800;
}

.session-list small {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.quick-card {
  display: grid;
  gap: 3px;
  width: 100%;
  min-height: 0;
  padding: 8px 9px;
  color: var(--text-primary);
  text-align: left;
  background: #ffffff;
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
  font-size: 12px;
  line-height: 1.45;
}

.admin-tip {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
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
  border-color: #cfe0ea;
}

.conversation {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding: 18px;
  background:
    linear-gradient(180deg, #fbfdff, #ffffff 34%),
    #ffffff;
  scroll-behavior: smooth;
}

.safety-note {
  padding: 9px 14px;
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
    height: auto;
    min-height: 0;
  }

  .chat-main {
    min-height: 640px;
  }
}

@media (max-width: 760px) {
  .chat-page {
    min-height: 100dvh;
    margin: -18px -16px -56px;
  }

  .chat-shell {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: calc(100dvh - 8px);
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  .chat-side {
    position: relative;
    z-index: 5;
    flex: 0 0 auto;
    gap: 8px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.96);
    border-bottom: 1px solid var(--border);
  }

  .assistant-card {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 10px;
    align-items: center;
    padding: 12px;
    box-shadow: none;
  }

  .assistant-badge {
    grid-column: 1 / -1;
    width: fit-content;
    margin-bottom: 0;
  }

  .assistant-card h2 {
    margin-bottom: 0;
    font-size: 15px;
  }

  .assistant-card p {
    display: none;
  }

  .new-session-btn {
    min-height: 34px;
    padding: 0 10px;
    font-size: 13px;
  }

  .side-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-height: 34px;
    color: var(--text-secondary);
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    font-weight: 800;
  }

  .side-toggle svg {
    transition: transform 0.2s ease;
  }

  .side-toggle svg.open {
    transform: rotate(180deg);
  }

  .side-content {
    display: none;
    max-height: 38dvh;
    overflow: auto;
  }

  .side-content.open {
    display: grid;
  }

  .session-panel,
  .quick-panel,
  .admin-tip {
    box-shadow: none;
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

  .conversation {
    order: 1;
    flex: 1 1 auto;
    min-height: 0;
    padding: 12px;
  }

  .safety-note {
    order: 2;
    padding: 8px 12px;
    border-top: 1px solid #fed7aa;
    font-size: 12px;
  }

  :deep(.composer) {
    position: sticky;
    bottom: 0;
    z-index: 6;
    order: 3;
    padding: 10px 10px calc(10px + env(safe-area-inset-bottom));
    box-shadow: 0 -12px 28px rgba(15, 23, 42, 0.08);
  }
}

@media (max-width: 640px) {
  .conversation {
    padding: 12px;
  }
}
</style>
