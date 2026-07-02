<template>
  <div class="page">
    <div class="page-title">
      <h2>多模态识别</h2>
      <p>
        支持图片上传、视频关键帧识别和语音症状输入。系统会返回基础视觉特征、拍摄质量提示、
        危险症状提醒和可继续问诊的文本结果。
      </p>
    </div>

    <div class="module-tabs">
      <button
        type="button"
        :class="{ active: activeModule === 'image' }"
        @click="activeModule = 'image'"
      >
        图片识别
      </button>
      <button
        type="button"
        :class="{ active: activeModule === 'video' }"
        @click="activeModule = 'video'"
      >
        视频识别
      </button>
      <button
        type="button"
        :class="{ active: activeModule === 'voice' }"
        @click="activeModule = 'voice'"
      >
        语音输入
      </button>
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
          placeholder="补充图片场景，例如：皮肤红疹、药盒说明书、咽喉不适等。"
        ></textarea>

        <button type="button" @click="analyzeImage" :disabled="imageLoading || !imagePreview">
          {{ imageLoading ? '识别中...' : '开始识别图片' }}
        </button>
      </div>

      <div class="preview-panel">
        <img v-if="imagePreview" :src="imagePreview" alt="上传图片预览" />
        <div v-else class="empty-state">等待上传图片</div>
      </div>

      <ResultBlock v-if="imageResult" title="图片识别结果" :result="imageResult" />
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
          placeholder="补充视频场景，例如：皮肤变化、药品包装、咽喉画面、症状动作等。"
        ></textarea>

        <div class="action-row">
          <button type="button" @click="extractVideoFrames" :disabled="frameLoading || !videoUrl">
            {{ frameLoading ? '抽帧中...' : '抽取关键帧' }}
          </button>
          <button type="button" @click="analyzeVideo" :disabled="videoLoading || framePreviews.length === 0">
            {{ videoLoading ? '识别中...' : '分析视频' }}
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

      <ResultBlock v-if="videoResult" title="视频识别结果" :result="videoResult" />
    </section>

    <section v-if="activeModule === 'voice'" class="voice-layout">
      <div class="tool-panel">
        <div class="panel-heading">
          <p>VOICE MODULE</p>
          <h3>语音症状输入</h3>
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

        <p v-if="!speechSupported" class="support-warning">
          当前浏览器不支持 Web Speech API，请使用 Chrome 或 Edge 体验语音输入。
        </p>

        <textarea
          v-model="voiceText"
          placeholder="语音识别结果会出现在这里，也可以手动修改后分析。"
        ></textarea>

        <div v-if="voiceInterim" class="interim-text">{{ voiceInterim }}</div>

        <div class="action-row">
          <button type="button" @click="analyzeVoice" :disabled="voiceLoading || !voiceText.trim()">
            {{ voiceLoading ? '分析中...' : '分析语音文本' }}
          </button>
          <button type="button" @click="submitVoiceChat" :disabled="chatLoading || !voiceText.trim()">
            {{ chatLoading ? '问诊中...' : '语音问诊' }}
          </button>
        </div>
      </div>

      <ResultBlock v-if="voiceResult" title="语音文本分析" :result="voiceResult" />

      <div v-if="voiceChatAnswer" class="chat-result">
        <h3>语音问诊结果</h3>
        <pre>{{ voiceChatAnswer }}</pre>
      </div>
    </section>

    <canvas ref="canvasRef" class="hidden-canvas"></canvas>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, ref } from 'vue'
import { apiUrl } from '../api'

const ResultBlock = defineComponent({
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
    const valueText = computed(() => JSON.stringify(props.result, null, 2))

    return () =>
      h('div', { class: 'result-block' }, [
        h('h3', props.title),
        h('pre', valueText.value),
      ])
  },
})

const activeModule = ref('image')

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
const voiceChatAnswer = ref('')
const voiceLoading = ref(false)
const chatLoading = ref(false)
const voiceListening = ref(false)
const recognition = ref(null)

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
const speechSupported = Boolean(SpeechRecognition)

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

  return response.json()
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
      message: '视频关键帧抽取失败，请换一个视频文件再试。',
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

const startVoice = () => {
  if (!speechSupported) {
    return
  }

  const instance = new SpeechRecognition()
  instance.lang = 'zh-CN'
  instance.continuous = true
  instance.interimResults = true

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
      voiceText.value = `${voiceText.value}${finalText}`.trim()
    }
    voiceInterim.value = interimText
  }

  instance.onend = () => {
    voiceListening.value = false
    voiceInterim.value = ''
  }

  recognition.value = instance
  voiceListening.value = true
  instance.start()
}

const stopVoice = () => {
  recognition.value?.stop()
  voiceListening.value = false
}

const clearVoice = () => {
  voiceText.value = ''
  voiceInterim.value = ''
  voiceResult.value = null
  voiceChatAnswer.value = ''
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

const submitVoiceChat = async () => {
  chatLoading.value = true
  voiceChatAnswer.value = ''

  try {
    const data = await postJson('/api/chat', {
      question: voiceText.value,
    })
    voiceChatAnswer.value = data.answer || '暂无回答。'
  } catch (error) {
    voiceChatAnswer.value = '语音问诊失败，请检查后端服务。'
    console.error(error)
  } finally {
    chatLoading.value = false
  }
}

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
  color: #64748b;
  line-height: 1.8;
}

.module-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 22px;
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
.result-block,
.chat-result {
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
.result-block h3,
.chat-result h3 {
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

.result-block,
.chat-result {
  grid-column: 1 / -1;
  padding: 20px;
}

.result-block pre,
.chat-result pre {
  max-height: 460px;
  margin-top: 12px;
  overflow: auto;
  color: #334155;
  white-space: pre-wrap;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  line-height: 1.75;
}

.support-warning {
  padding: 12px 14px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-weight: 800;
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
