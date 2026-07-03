<template>
  <div class="page">
    <div class="page-title">
      <h2>多模态识别</h2>
      <p>上传图片、抽取视频关键帧，或用语音整理症状。页面只展示整理后的结论、依据和下一步建议。</p>
    </div>

    <div class="module-tabs">
      <button type="button" :class="{ active: activeModule === 'image' }" @click="activeModule = 'image'">
        图片识别
      </button>
      <button type="button" :class="{ active: activeModule === 'video' }" @click="activeModule = 'video'">
        视频识别
      </button>
      <button type="button" :class="{ active: activeModule === 'voice' }" @click="activeModule = 'voice'">
        语音输入
      </button>
    </div>

    <div class="status-panel">
      <div>
        <strong>视觉模型状态</strong>
        <span>{{ multimodalStatusText }}</span>
      </div>
      <div>
        <strong>当前链路</strong>
        <span>图片/视频 → 视觉分析 → 数据库命中 → RAG补充 → 就诊建议</span>
      </div>
    </div>

    <section v-if="activeModule === 'image'" class="module-layout">
      <div class="tool-panel">
        <div class="panel-heading">
          <p>IMAGE MODULE</p>
          <h3>图片识别</h3>
        </div>

        <label class="file-picker">
          <input type="file" accept="image/*" @change="handleImageFile" />
          <span>{{ imageFileName || '选择图片' }}</span>
        </label>

        <textarea
          v-model="imageNote"
          placeholder="补充图片背景，例如：皮肤红疹三天、喉咙痛、药盒说明书、伤口变化等。"
        ></textarea>

        <button type="button" @click="analyzeImage" :disabled="imageLoading || !imagePreview">
          {{ imageLoading ? '识别中...' : '开始识别图片' }}
        </button>
      </div>

      <div class="preview-panel">
        <img v-if="imagePreview" :src="imagePreview" alt="上传图片预览" />
        <div v-else class="empty-state">等待上传图片</div>
      </div>

      <AnswerBlock v-if="imageResult" title="图片识别结果" :result="imageResult" />
    </section>

    <section v-if="activeModule === 'video'" class="module-layout">
      <div class="tool-panel">
        <div class="panel-heading">
          <p>VIDEO MODULE</p>
          <h3>视频关键帧识别</h3>
        </div>

        <label class="file-picker">
          <input type="file" accept="video/*" @change="handleVideoFile" />
          <span>{{ videoFileName || '选择视频' }}</span>
        </label>

        <textarea
          v-model="videoNote"
          placeholder="补充视频背景，例如：皮肤变化、药品包装、咽喉画面、症状动作等。"
        ></textarea>

        <div class="action-row">
          <button type="button" @click="extractVideoFrames" :disabled="frameLoading || !videoUrl">
            {{ frameLoading ? '抽帧中...' : '抽取关键帧' }}
          </button>
          <button type="button" @click="analyzeVideo" :disabled="videoLoading || framePreviews.length === 0">
            {{ videoLoading ? '分析中...' : '分析视频' }}
          </button>
        </div>
      </div>

      <div class="video-area">
        <video
          v-if="videoUrl"
          ref="videoRef"
          :src="videoUrl"
          controls
          muted
          preload="metadata"
          @loadedmetadata="syncVideoDuration"
        ></video>
        <div v-else class="empty-state">等待上传视频</div>
      </div>

      <div v-if="framePreviews.length" class="frame-strip">
        <figure v-for="frame in framePreviews" :key="frame.timestamp">
          <img :src="frame.image" alt="视频关键帧" />
          <figcaption>{{ frame.timestamp.toFixed(1) }}s</figcaption>
        </figure>
      </div>

      <AnswerBlock v-if="videoResult" title="视频识别结果" :result="videoResult" />
    </section>

    <section v-if="activeModule === 'voice'" class="voice-layout">
      <div class="tool-panel">
        <div class="panel-heading">
          <p>VOICE MODULE</p>
          <h3>语音症状输入</h3>
        </div>

        <div class="voice-status" :class="{ warning: voiceError }">
          {{ voiceError || voiceStatus }}
        </div>

        <div class="voice-controls">
          <button type="button" @click="startVoice" :disabled="voiceListening || !speechSupported">
            {{ voiceListening ? '识别中...' : '开始语音输入' }}
          </button>
          <button type="button" class="secondary" @click="stopVoice" :disabled="!voiceListening">
            停止
          </button>
          <button type="button" class="secondary" @click="clearVoice">
            清空
          </button>
        </div>

        <textarea
          v-model="voiceText"
          placeholder="语音识别文本会出现在这里；也可以直接输入或修改后分析。"
        ></textarea>

        <div v-if="voiceInterim" class="interim-text">{{ voiceInterim }}</div>

        <button type="button" @click="analyzeVoice" :disabled="voiceLoading || !voiceText.trim()">
          {{ voiceLoading ? '分析中...' : '分析症状文本' }}
        </button>
      </div>

      <AnswerBlock v-if="voiceResult" title="语音文本分析" :result="voiceResult" />
    </section>

    <canvas ref="canvasRef" class="hidden-canvas"></canvas>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiUrl } from '../api'

const toList = (value) => {
  if (!value) {
    return []
  }
  return Array.isArray(value) ? value.filter(Boolean) : [value]
}

const summarizeDatabaseMatches = (context) => {
  if (!context) {
    return []
  }

  const diseaseItems = (context.diseases || []).map((item) => {
    const matches = toList(item.matched_fields).join('；')
    return `疾病：${item.title}${matches ? `（${matches}）` : ''}`
  })
  const medicineItems = (context.medicines || []).map((item) => {
    const matches = toList(item.matched_fields).join('；')
    return `药品：${item.title}${matches ? `（${matches}）` : ''}`
  })

  return [...diseaseItems, ...medicineItems].slice(0, 6)
}

const summarizeRetrievedDocs = (docs) => (
  toList(docs)
    .map((doc) => `${doc.doc_type === 'medicine' ? '药品' : '疾病'}：${doc.title}（相似度 ${Number(doc.score || 0).toFixed(3)}）`)
    .slice(0, 6)
)

const AnswerBlock = defineComponent({
  props: {
    title: {
      type: String,
      required: true,
    },
    result: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const answer = computed(() => props.result.answer || {})

    const visitAdvice = (value) => {
      if (!value.visit_advice) {
        return null
      }

      const advice = value.visit_advice

      return h('div', { class: 'visit-advice' }, [
        h('h4', '建议就诊'),
        h('div', { class: 'visit-grid' }, [
          h('p', [h('strong', '处理级别：'), advice.urgency || '请结合症状观察']),
          h('p', [h('strong', '建议时间：'), advice.timing || '症状持续或加重时就医']),
          h('p', [h('strong', '建议科室：'), advice.department || '全科或普通内科']),
          h('p', [h('strong', '原因：'), advice.reason || '需要结合症状和医生面诊判断']),
        ]),
      ])
    }

    const section = (title, items) => {
      const list = toList(items)
      if (!list.length) {
        return null
      }

      return h('div', { class: 'answer-section' }, [
        h('h4', title),
        h('ul', list.map((item) => h('li', String(item)))),
      ])
    }

    const llmStatus = (llm) => {
      if (!llm) {
        return null
      }

      const text = llm.used
        ? `视觉模型已参与识别：${llm.model || llm.provider || '已配置模型'}`
        : `视觉模型未启用：${llm.error || '当前使用本地分析、数据库和RAG'}`

      return h('p', { class: ['source-note', llm.used ? 'source-ok' : 'source-warn'] }, text)
    }

    return () => {
      const value = answer.value
      const risk = value.risk_level || '未知'
      const databaseMatches = summarizeDatabaseMatches(props.result.database_context)
      const retrievedDocs = summarizeRetrievedDocs(props.result.retrieved_docs)

      return h('article', { class: ['answer-card', props.result.success ? 'ok' : 'error'] }, [
        h('div', { class: 'answer-heading' }, [
          h('div', [
            h('p', props.title),
            h('h3', value.title || props.title),
          ]),
          h('span', { class: ['risk-pill', `risk-${risk}`] }, `风险：${risk}`),
        ]),
        llmStatus(props.result.llm),
        h('p', { class: 'conclusion' }, value.conclusion || props.result.message || '暂未生成结论。'),
        visitAdvice(value),
        section('可能的病状方向', value.possible_conditions),
        section('现在可以做什么', value.actions),
        section('用药提醒', value.medication_reminder),
        section('需要立刻或尽快就医的情况', value.red_flags),
        section('系统依据', value.evidence),
        section('画面观察', props.result.observations),
        section('拍摄建议', props.result.capture_tips),
        section('数据库命中', databaseMatches),
        section('RAG检索依据', retrievedDocs),
        section('还需要补充的信息', value.follow_up_questions),
        h('p', { class: 'notice' }, value.medical_notice || props.result.medical_notice || '本结果不能替代医生诊断或药师指导。'),
      ])
    }
  },
})

const activeModule = ref('image')
const multimodalStatus = ref(null)

const imagePreview = ref('')
const imageFileName = ref('')
const imageNote = ref('')
const imageResult = ref(null)
const imageLoading = ref(false)

const videoRef = ref(null)
const canvasRef = ref(null)
const videoUrl = ref('')
const videoFileName = ref('')
const videoNote = ref('')
const videoDuration = ref(0)
const framePreviews = ref([])
const frameLoading = ref(false)
const videoLoading = ref(false)
const videoResult = ref(null)

const voiceText = ref('')
const voiceInterim = ref('')
const voiceResult = ref(null)
const voiceLoading = ref(false)
const voiceListening = ref(false)
const voiceStatus = ref('语音识别准备就绪')
const voiceError = ref('')
const recognition = ref(null)

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
const speechSupported = Boolean(SpeechRecognition)
const multimodalStatusText = computed(() => (
  multimodalStatus.value?.message || '正在检测多模态服务状态...'
))

if (!speechSupported) {
  voiceStatus.value = '当前浏览器不支持语音识别，可直接输入文字后分析'
}

const readFileAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })

const postJson = async (path, body) => {
  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({
    success: false,
    message: '服务返回内容无法解析。',
  }))

  if (!response.ok) {
    return {
      success: false,
      message: data.message || data.detail || `请求失败：${response.status}`,
      answer: data.answer,
    }
  }

  return data
}

const loadMultimodalStatus = async () => {
  try {
    const response = await fetch(apiUrl('/api/multimodal/status'))
    multimodalStatus.value = await response.json()
  } catch (error) {
    multimodalStatus.value = {
      vision_llm_available: false,
      message: '多模态状态获取失败，请检查后端服务。',
    }
    console.error(error)
  }
}

const handleImageFile = async (event) => {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  imageFileName.value = file.name
  imagePreview.value = await readFileAsDataUrl(file)
  imageResult.value = null
}

const analyzeImage = async () => {
  imageLoading.value = true
  imageResult.value = null

  try {
    imageResult.value = await postJson('/api/multimodal/image/analyze', {
      image: imagePreview.value,
      file_name: imageFileName.value,
      note: imageNote.value,
    })
  } catch (error) {
    imageResult.value = {
      success: false,
      message: '图片识别请求失败，请检查后端服务。',
    }
    console.error(error)
  } finally {
    imageLoading.value = false
  }
}

const handleVideoFile = (event) => {
  const file = event.target.files?.[0]
  if (!file) {
    return
  }

  if (videoUrl.value) {
    URL.revokeObjectURL(videoUrl.value)
  }

  videoFileName.value = file.name
  videoUrl.value = URL.createObjectURL(file)
  videoResult.value = null
  framePreviews.value = []
}

const syncVideoDuration = () => {
  videoDuration.value = videoRef.value?.duration || 0
}

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
    }, 1200)

    const onSeeked = () => {
      window.clearTimeout(timeout)
      video.removeEventListener('seeked', onSeeked)
      resolve()
    }
    video.addEventListener('seeked', onSeeked)
    video.currentTime = Math.min(Math.max(timestamp, 0), Math.max(video.duration - 0.1, 0))
  })

const captureFrame = async (timestamp) => {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) {
    return null
  }

  await seekVideo(timestamp)

  const width = video.videoWidth || 640
  const height = video.videoHeight || 360
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, width, height)

  return {
    timestamp,
    image: canvas.toDataURL('image/jpeg', 0.86),
  }
}

const extractVideoFrames = async () => {
  const video = videoRef.value
  if (!video) {
    return
  }

  frameLoading.value = true
  videoResult.value = null

  try {
    const duration = video.duration || videoDuration.value || 0
    const times = duration > 2
      ? [0.1, duration * 0.25, duration * 0.5, duration * 0.75, Math.max(duration - 0.2, 0.1)]
      : [0.1]

    const frames = []
    for (const time of times) {
      const frame = await captureFrame(time)
      if (frame) {
        frames.push(frame)
      }
    }

    framePreviews.value = frames
  } catch (error) {
    videoResult.value = {
      success: false,
      message: '视频关键帧抽取失败，请更换视频文件再试。',
    }
    console.error(error)
  } finally {
    frameLoading.value = false
  }
}

const analyzeVideo = async () => {
  videoLoading.value = true
  videoResult.value = null

  try {
    videoResult.value = await postJson('/api/multimodal/video/analyze', {
      frames: framePreviews.value,
      file_name: videoFileName.value,
      note: videoNote.value,
      duration: videoDuration.value,
    })
  } catch (error) {
    videoResult.value = {
      success: false,
      message: '视频识别请求失败，请检查后端服务。',
    }
    console.error(error)
  } finally {
    videoLoading.value = false
  }
}

const voiceErrorText = (error) => {
  const messages = {
    'not-allowed': '麦克风权限被拒绝，可改用文本输入。',
    'no-speech': '没有识别到语音，请靠近麦克风后重试。',
    network: '语音识别网络异常，可改用文本输入。',
    'audio-capture': '没有检测到可用麦克风。',
    aborted: '语音识别已停止。',
  }

  return messages[error] || '语音识别暂时不可用，可直接输入文字分析。'
}

const startVoice = () => {
  if (!speechSupported) {
    voiceError.value = '当前浏览器不支持语音识别，可直接输入文字分析。'
    return
  }

  if (voiceListening.value) {
    return
  }

  voiceError.value = ''
  voiceInterim.value = ''

  const instance = new SpeechRecognition()
  instance.lang = 'zh-CN'
  instance.continuous = true
  instance.interimResults = true

  instance.onstart = () => {
    voiceListening.value = true
    voiceStatus.value = '正在识别语音'
  }

  instance.onresult = (event) => {
    let finalText = ''
    let interimText = ''

    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0].transcript
      if (event.results[index].isFinal) {
        finalText += transcript
      } else {
        interimText += transcript
      }
    }

    if (finalText) {
      const separator = voiceText.value && !/[，。！？；,.!?;]$/.test(voiceText.value) ? '，' : ''
      voiceText.value = `${voiceText.value}${separator}${finalText}`.trim()
    }
    voiceInterim.value = interimText
  }

  instance.onerror = (event) => {
    voiceError.value = voiceErrorText(event.error)
    voiceListening.value = false
    voiceStatus.value = '语音识别已停止'
  }

  instance.onend = () => {
    voiceListening.value = false
    voiceInterim.value = ''
    if (!voiceError.value) {
      voiceStatus.value = voiceText.value ? '语音识别完成，可修改后分析' : '语音识别已停止'
    }
  }

  recognition.value = instance

  try {
    instance.start()
  } catch (error) {
    voiceError.value = '语音识别启动失败，可直接输入文字分析。'
    voiceListening.value = false
    console.error(error)
  }
}

const stopVoice = () => {
  recognition.value?.stop()
  voiceListening.value = false
}

const clearVoice = () => {
  voiceText.value = ''
  voiceInterim.value = ''
  voiceResult.value = null
  voiceError.value = ''
  voiceStatus.value = speechSupported ? '语音识别准备就绪' : '当前浏览器不支持语音识别，可直接输入文字后分析'
}

const analyzeVoice = async () => {
  voiceLoading.value = true
  voiceResult.value = null

  try {
    voiceResult.value = await postJson('/api/multimodal/voice/analyze', {
      transcript: voiceText.value,
    })
  } catch (error) {
    voiceResult.value = {
      success: false,
      message: '语音文本分析失败，请检查后端服务。',
    }
    console.error(error)
  } finally {
    voiceLoading.value = false
  }
}

onMounted(() => {
  loadMultimodalStatus()
})

onBeforeUnmount(() => {
  recognition.value?.stop()
  if (videoUrl.value) {
    URL.revokeObjectURL(videoUrl.value)
  }
})
</script>

<style scoped>
.page-title {
  margin-bottom: 22px;
}

.page-title h2 {
  color: #111827;
  font-size: 30px;
  margin-bottom: 10px;
}

.page-title p {
  max-width: 920px;
  color: #64748b;
  line-height: 1.8;
}

.module-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 22px;
}

.status-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.status-panel div {
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.status-panel strong,
.status-panel span {
  display: block;
}

.status-panel strong {
  margin-bottom: 4px;
  color: #111827;
  font-size: 13px;
  font-weight: 900;
}

.status-panel span {
  color: #475569;
  line-height: 1.6;
}

.module-tabs button,
button {
  min-height: 42px;
  padding: 0 16px;
  color: #ffffff;
  background: #2563eb;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
}

.module-tabs button {
  color: #334155;
  background: #ffffff;
  border: 1px solid #dbe6f0;
}

.module-tabs button.active {
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
}

button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

button.secondary {
  color: #2563eb;
  background: #eff6ff;
}

.module-layout,
.voice-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) minmax(320px, 1.1fr);
  gap: 18px;
}

.voice-layout {
  grid-template-columns: minmax(320px, 0.9fr) minmax(320px, 1.1fr);
}

.tool-panel,
.preview-panel,
.video-area,
.answer-card,
.metrics-panel {
  background: #ffffff;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.tool-panel {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 22px;
}

.panel-heading p {
  margin-bottom: 6px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.panel-heading h3,
.answer-card h3,
.metrics-panel h3 {
  color: #111827;
  font-size: 22px;
  font-weight: 900;
}

.file-picker {
  display: grid;
  min-height: 48px;
  place-items: center;
  color: #2563eb;
  background: #eff6ff;
  border: 1px dashed #93c5fd;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 800;
}

.file-picker input {
  display: none;
}

textarea {
  width: 100%;
  min-height: 118px;
  padding: 14px;
  color: #1f2937;
  background: #f8fbfd;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
  resize: vertical;
  line-height: 1.7;
  outline: none;
}

textarea:focus {
  background: #ffffff;
  border-color: #2563eb;
}

.preview-panel,
.video-area {
  display: grid;
  min-height: 320px;
  place-items: center;
  overflow: hidden;
}

.preview-panel img,
.video-area video {
  width: 100%;
  max-height: 520px;
  object-fit: contain;
}

.empty-state {
  color: #64748b;
  font-weight: 800;
}

.action-row,
.voice-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.frame-strip {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.frame-strip figure {
  margin: 0;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
}

.frame-strip img {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.frame-strip figcaption {
  padding: 8px 10px;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.answer-card,
.metrics-panel {
  grid-column: 1 / -1;
  padding: 20px;
}

.answer-card.error {
  border-color: #fecaca;
  background: #fff7f7;
}

.answer-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.answer-heading p {
  margin-bottom: 4px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
}

.risk-pill,
.model-chip {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}

.risk-低 {
  color: #166534;
  background: #dcfce7;
}

.risk-中 {
  color: #92400e;
  background: #fef3c7;
}

.risk-高 {
  color: #991b1b;
  background: #fee2e2;
}

.risk-未知 {
  color: #475569;
  background: #e2e8f0;
}

.conclusion {
  color: #111827;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.75;
}

.scene-line,
.notice {
  margin-top: 10px;
  color: #475569;
  line-height: 1.7;
}

.source-note {
  margin: -4px 0 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-weight: 800;
  line-height: 1.6;
}

.source-ok {
  color: #166534;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.source-warn {
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.visit-advice {
  margin-top: 16px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #dbe6f0;
  border-radius: 8px;
}

.visit-advice h4 {
  margin-bottom: 10px;
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.visit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.visit-grid p {
  margin: 0;
  color: #334155;
  line-height: 1.7;
}

.visit-grid strong {
  color: #111827;
}

.answer-section {
  margin-top: 16px;
}

.answer-section h4 {
  margin-bottom: 8px;
  color: #334155;
  font-size: 15px;
  font-weight: 900;
}

.answer-section ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
  color: #1f2937;
  line-height: 1.7;
}

.model-chip {
  margin-top: 14px;
  color: #155e75;
  background: #cffafe;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.metrics-grid span {
  padding: 10px 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 800;
}

.voice-status {
  padding: 12px 14px;
  color: #155e75;
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 8px;
  font-weight: 800;
  line-height: 1.6;
}

.voice-status.warning {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.interim-text {
  padding: 10px 12px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  line-height: 1.7;
}

.hidden-canvas {
  display: none;
}

@media (max-width: 860px) {
  .module-layout,
  .voice-layout {
    grid-template-columns: 1fr;
  }
}
</style>
