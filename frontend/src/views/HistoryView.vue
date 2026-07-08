<template>
  <div class="page">
    <div class="page-title">
      <h2>问答历史记录</h2>
      <p>
        系统会自动保存最近的 AI 医疗助手对话，便于查看用户问题、系统回答、危险提醒和检索结果。
      </p>
    </div>

    <div class="toolbar">
      <button @click="loadHistory(true)" :disabled="loading">
        {{ loading ? '加载中...' : '刷新记录' }}
      </button>

      <button class="clear-btn" @click="clearHistory">
        清空历史
      </button>
    </div>

    <div v-if="historyList.length === 0" class="empty">
      暂无历史记录，请先到“AI 助手”页面进行咨询。
    </div>

    <div v-for="item in historyList" :key="item.id" class="history-card">
      <div class="card-header">
        <div>
          <strong>问题：{{ displayQuestion(item.question) }}</strong>
          <span>{{ item.create_time }}</span>
        </div>
        <button
          v-if="item.session_id"
          type="button"
          class="continue-btn"
          @click="continueConversation(item.session_id)"
        >
          继续对话
        </button>
      </div>

      <div v-if="hasImageInput(item.question)" class="input-tag">
        已上传图片，图片识别信息已作为 AI 分析输入。
      </div>

      <div
        v-if="item.warning && item.warning.has_warning"
        class="warning"
      >
        危险提醒：{{ item.warning.matched.join('、') }}
      </div>

      <div class="answer">
        <h4>系统回答</h4>
        <pre>{{ item.answer }}</pre>
      </div>

      <div
        v-if="item.retrieved_docs && item.retrieved_docs.length > 0"
        class="docs"
      >
        <h4>检索到的知识</h4>

        <div
          v-for="(doc, index) in item.retrieved_docs"
          :key="index"
          class="doc-item"
        >
          {{ index + 1 }}. {{ doc.title }}
          <span>{{ doc.doc_type === 'disease' ? '常见病' : '药品' }}</span>
        </div>
      </div>

      <div class="feedback">
        <div class="feedback-title">
          <strong>回答评价</strong>
          <span v-if="item.rating">当前评分：{{ item.rating }} 星</span>
          <span v-else>还没有评价</span>
        </div>

        <div class="feedback-editor">
          <div class="star-rating" aria-label="五星评价">
            <button
              v-for="star in 5"
              :key="star"
              type="button"
              :class="{ active: star <= getDraft(item).rating }"
              @click="getDraft(item).rating = star"
            >
              ★
            </button>
          </div>

          <textarea
            v-model="getDraft(item).feedbackText"
            placeholder="填写详细评价，例如：回答是否准确、是否看得懂、还需要补充哪些内容。"
          ></textarea>

          <button
            class="feedback-submit"
            @click="submitFeedback(item.id)"
            :disabled="!getDraft(item).rating"
          >
            保存评价
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiUrl, cachedGetJson, clearPageCache } from '../api'

const router = useRouter()
const historyList = ref([])
const loading = ref(false)
const feedbackDrafts = reactive({})

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

const getDraft = (item) => {
  if (!feedbackDrafts[item.id]) {
    feedbackDrafts[item.id] = {
      rating: Number(item.rating || 0),
      feedbackText: item.feedback_text || '',
    }
  }

  return feedbackDrafts[item.id]
}

const syncFeedbackDrafts = () => {
  historyList.value.forEach((item) => {
    feedbackDrafts[item.id] = {
      rating: Number(item.rating || 0),
      feedbackText: item.feedback_text || '',
    }
  })
}

const historyCacheKey = () => {
  const raw = localStorage.getItem('ragUser')
  const user = raw ? JSON.parse(raw) : null
  return `history:list:${user?.id || user?.username || 'guest'}`
}

const displayQuestion = (question = '') => {
  const text = String(question || '').trim()
  const [userText] = text.split('图片识别描述：')
  const cleaned = userText.replace(/。+$/g, '').trim()

  if (cleaned) {
    return cleaned
  }

  if (hasImageInput(text)) {
    return '图片咨询'
  }

  return text
}

const hasImageInput = (question = '') => {
  const text = String(question || '')
  return text.includes('图片识别描述：') || text.includes('图片识别标签：')
}

const loadHistory = async (force = false) => {
  loading.value = true

  try {
    const data = await cachedGetJson(historyCacheKey(), '/api/history/list', {
      force,
      fetchOptions: {
        headers: authHeaders(),
      },
    })

    historyList.value = data.data || []
    syncFeedbackDrafts()
  } catch (error) {
    alert('加载历史记录失败，请检查后端服务是否正常运行。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const clearHistory = async () => {
  const confirmClear = confirm('确定要清空所有历史记录吗？')

  if (!confirmClear) {
    return
  }

  try {
    await fetch(apiUrl('/api/history/clear'), {
      method: 'POST',
      headers: authHeaders(),
    })

    historyList.value = []
    clearPageCache(historyCacheKey())
  } catch (error) {
    alert('清空失败，请检查后端服务是否正常运行。')
    console.error(error)
  }
}

const continueConversation = (sessionId) => {
  router.push({
    path: '/chat',
    query: {
      session_id: sessionId,
    },
  })
}

const submitFeedback = async (recordId) => {
  const draft = feedbackDrafts[recordId]

  if (!draft?.rating) {
    alert('请先选择星级')
    return
  }

  try {
    const response = await fetch(apiUrl(`/api/history/${recordId}/feedback`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        rating: draft.rating,
        feedback_text: draft.feedbackText,
      }),
    })

    const data = await response.json()

    if (data.success) {
      clearPageCache(historyCacheKey())
      await loadHistory(true)
    } else {
      alert(data.message || '反馈保存失败')
    }
  } catch (error) {
    alert('反馈保存失败，请检查后端服务是否正常运行。')
    console.error(error)
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.page-title {
  margin-bottom: 24px;
}

.page-title h2 {
  font-size: 30px;
  margin-bottom: 10px;
  color: #111827;
}

.page-title p {
  color: #6b7280;
  line-height: 1.8;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

button {
  padding: 11px 22px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}

button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.clear-btn {
  background: #dc2626;
}

.empty {
  background: white;
  padding: 28px;
  border-radius: 16px;
  color: #6b7280;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.history-card {
  background: white;
  margin-bottom: 22px;
  padding: 24px;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 14px;
  margin-bottom: 16px;
}

.card-header > div {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.card-header strong {
  color: #111827;
}

.card-header span {
  color: #6b7280;
  font-size: 14px;
}

.continue-btn {
  flex: 0 0 auto;
  min-height: 36px;
  padding: 0 14px;
  color: #0f766e;
  background: #ccfbf1;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  font-size: 14px;
}

.continue-btn:hover {
  background: #99f6e4;
}

.input-tag {
  width: max-content;
  margin-bottom: 14px;
  padding: 6px 10px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
}

.warning {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 12px 16px;
  border-radius: 10px;
  margin-bottom: 16px;
}

.answer h4,
.docs h4 {
  color: #2563eb;
  margin-bottom: 10px;
}

pre {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 15px;
  color: #374151;
  font-family: "Microsoft YaHei", Arial, sans-serif;
}

.docs {
  margin-top: 18px;
}

.doc-item {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 12px 14px;
  border-radius: 10px;
  margin-top: 10px;
}

.doc-item span {
  margin-left: 8px;
  font-size: 12px;
  color: white;
  background: #2563eb;
  padding: 3px 8px;
  border-radius: 999px;
}

.feedback {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.feedback-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.feedback-title strong,
.feedback-title span {
  display: block;
}

.feedback-title strong {
  color: #111827;
}

.feedback-title span {
  color: #6b7280;
  font-size: 13px;
  font-weight: 700;
}

.feedback-editor {
  display: grid;
  gap: 12px;
}

.star-rating {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.star-rating button {
  display: grid;
  width: 38px;
  height: 38px;
  min-height: 38px;
  place-items: center;
  padding: 0;
  color: #cbd5e1;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 22px;
  line-height: 1;
}

.star-rating button.active {
  color: #d97706;
  background: #fff7ed;
  border-color: #fed7aa;
}

.feedback textarea {
  width: 100%;
  min-height: 88px;
  padding: 12px;
  color: #374151;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  resize: vertical;
  outline: none;
  line-height: 1.7;
}

.feedback textarea:focus {
  background: #ffffff;
  border-color: #2563eb;
}

.feedback-submit {
  justify-self: start;
  min-height: 38px;
  padding: 0 16px;
}

@media (max-width: 640px) {
  .card-header {
    flex-direction: column;
  }

  .feedback-title {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
