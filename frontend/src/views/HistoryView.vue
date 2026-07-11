<template>
  <div class="history-page">
    <header class="page-title ui-page-heading">
      <span class="page-kicker">CONSULTATION ARCHIVE</span>
      <div class="heading-row">
        <div>
          <h2>我的咨询记录</h2>
          <p>回看每一次健康咨询、知识引用与风险提示，也可以从任意记录继续对话。</p>
        </div>
        <div class="heading-actions">
          <button class="ui-button ui-button--soft" :disabled="loading" @click="loadHistory(true)">
            <RefreshCw :class="{ spin: loading }" :size="17" aria-hidden="true" />
            {{ loading ? '正在刷新' : '刷新记录' }}
          </button>
          <button class="clear-btn ui-button" :disabled="historyList.length === 0" @click="clearHistory">
            <Trash2 :size="17" aria-hidden="true" />
            清空记录
          </button>
        </div>
      </div>
    </header>

    <section class="records-toolbar ui-card" aria-label="记录筛选与分页设置">
      <div class="records-summary">
        <span class="summary-icon"><Archive :size="18" aria-hidden="true" /></span>
        <div>
          <strong>{{ filteredHistory.length }}</strong>
          <span>条可查看记录</span>
        </div>
      </div>

      <label class="history-search">
        <Search :size="17" aria-hidden="true" />
        <input
          v-model="searchQuery"
          type="search"
          placeholder="搜索问题或回答内容"
          aria-label="搜索咨询记录"
        />
        <button v-if="searchQuery" type="button" aria-label="清空搜索" @click="searchQuery = ''">
          <X :size="15" aria-hidden="true" />
        </button>
      </label>

      <label class="page-size-control">
        每页
        <select v-model.number="pageSize" aria-label="每页显示记录数">
          <option v-for="option in pageSizeOptions" :key="option" :value="option">{{ option }}</option>
        </select>
        条
      </label>
    </section>

    <div v-if="loading && historyList.length === 0" class="empty ui-empty">
      正在整理您的咨询记录...
    </div>

    <div v-else-if="historyList.length === 0" class="empty ui-empty">
      暂无历史记录，请先到“AI 咨询”页面开始一次对话。
    </div>

    <div v-else-if="filteredHistory.length === 0" class="empty ui-empty">
      没有找到与“{{ searchQuery }}”匹配的记录，请尝试其他关键词。
    </div>

    <section v-else class="history-list" aria-label="咨询记录列表">
      <article v-for="(item, index) in pagedHistory" :key="item.id" class="history-card ui-card">
      <div class="card-header">
        <span class="record-index">{{ startIndex + index + 1 }}</span>
        <div class="question-block">
          <span class="question-label">我的问题</span>
          <strong>{{ displayQuestion(item.question) }}</strong>
          <span class="record-time">
            <CalendarDays :size="14" aria-hidden="true" />
            {{ item.create_time }}
          </span>
        </div>
        <button
          v-if="item.session_id"
          type="button"
          class="continue-btn ui-button ui-button--soft"
          @click="continueConversation(item.session_id)"
        >
          <MessageSquareMore :size="16" aria-hidden="true" />
          继续对话
        </button>
      </div>

      <div v-if="hasImageInput(item.question)" class="input-tag ui-badge ui-badge--info">
        已上传图片，图片识别信息已作为 AI 分析输入。
      </div>

      <div
        v-if="item.warning && item.warning.has_warning"
        class="warning ui-alert ui-alert--error"
      >
        <strong>危险提醒</strong>
        <span>{{ item.warning.matched?.join('、') || item.warning.message }}</span>
      </div>

      <div class="answer">
        <div class="answer-heading">
          <span class="ai-mark">AI</span>
          <h4>系统回答</h4>
        </div>
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
            class="ui-textarea"
            v-model="getDraft(item).feedbackText"
            placeholder="填写详细评价，例如：回答是否准确、是否看得懂、还需要补充哪些内容。"
          ></textarea>

          <button
            class="feedback-submit ui-button ui-button--primary"
            @click="submitFeedback(item.id)"
            :disabled="!getDraft(item).rating"
          >
            保存评价
          </button>
        </div>
      </div>
      </article>
    </section>

    <nav v-if="filteredHistory.length > 0" class="pagination-bar" aria-label="咨询记录分页">
      <span>第 {{ currentPage }} / {{ totalPages }} 页 · 显示 {{ displayStart }}–{{ displayEnd }} 条</span>
      <div class="pager-buttons">
        <button type="button" aria-label="第一页" :disabled="currentPage === 1" @click="currentPage = 1">
          <ChevronsLeft :size="18" aria-hidden="true" />
        </button>
        <button type="button" aria-label="上一页" :disabled="currentPage === 1" @click="currentPage -= 1">
          <ChevronLeft :size="18" aria-hidden="true" />
        </button>
        <button
          v-for="page in visiblePageNumbers"
          :key="page"
          type="button"
          class="page-number"
          :class="{ active: page === currentPage }"
          :aria-current="page === currentPage ? 'page' : undefined"
          :aria-label="`第 ${page} 页`"
          @click="currentPage = page"
        >
          {{ page }}
        </button>
        <button type="button" aria-label="下一页" :disabled="currentPage === totalPages" @click="currentPage += 1">
          <ChevronRight :size="18" aria-hidden="true" />
        </button>
        <button type="button" aria-label="最后一页" :disabled="currentPage === totalPages" @click="currentPage = totalPages">
          <ChevronsRight :size="18" aria-hidden="true" />
        </button>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Archive,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  MessageSquareMore,
  RefreshCw,
  Search,
  Trash2,
  X,
} from '@lucide/vue'
import { apiUrl, cachedGetJson, clearPageCache } from '../api'

const router = useRouter()
const historyList = ref([])
const loading = ref(false)
const feedbackDrafts = reactive({})
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(5)
const pageSizeOptions = [5, 10, 20]

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

const filteredHistory = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return historyList.value

  return historyList.value.filter((item) => [
    displayQuestion(item.question),
    item.answer,
    item.create_time,
    ...(item.retrieved_docs || []).map((doc) => doc.title),
  ].filter(Boolean).join(' ').toLowerCase().includes(query))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredHistory.value.length / pageSize.value)))
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const displayStart = computed(() => (filteredHistory.value.length ? startIndex.value + 1 : 0))
const displayEnd = computed(() => Math.min(filteredHistory.value.length, startIndex.value + pageSize.value))
const pagedHistory = computed(() => filteredHistory.value.slice(startIndex.value, startIndex.value + pageSize.value))

const visiblePageNumbers = computed(() => {
  const maxVisible = 5
  let firstPage = Math.max(1, currentPage.value - 2)
  const lastPage = Math.min(totalPages.value, firstPage + maxVisible - 1)
  firstPage = Math.max(1, lastPage - maxVisible + 1)

  return Array.from({ length: lastPage - firstPage + 1 }, (_, index) => firstPage + index)
})

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
    currentPage.value = 1
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

watch([searchQuery, pageSize], () => {
  currentPage.value = 1
})

watch(totalPages, (value) => {
  if (currentPage.value > value) currentPage.value = value
})

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.history-page {
  display: grid;
  gap: 20px;
}

.page-title {
  position: relative;
  margin-bottom: 2px;
  padding: 26px 28px;
  overflow: hidden;
  background:
    radial-gradient(circle at 94% 12%, rgba(37, 99, 235, 0.11), transparent 30%),
    linear-gradient(135deg, rgba(240, 253, 250, 0.92), rgba(255, 255, 255, 0.97) 54%, rgba(239, 246, 255, 0.9));
  border: 1px solid #dce7f2;
  border-radius: 22px;
  box-shadow: 0 18px 45px rgba(27, 57, 91, 0.07);
}

.page-kicker {
  color: var(--teal);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.15em;
}

.heading-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.heading-row p {
  margin-top: 8px;
}

.heading-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
}

.clear-btn {
  color: #b42318;
  background: #fff;
  border-color: #f5d0cc;
}

.clear-btn:hover:not(:disabled) {
  color: #991b1b;
  background: var(--danger-soft);
  border-color: #fca5a5;
}

.records-toolbar {
  display: grid;
  grid-template-columns: auto minmax(240px, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
}

.records-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 18px;
  border-right: 1px solid var(--border);
}

.summary-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: var(--teal);
  background: var(--teal-soft);
  border-radius: 12px;
}

.records-summary div {
  display: flex;
  align-items: baseline;
  gap: 5px;
  white-space: nowrap;
}

.records-summary strong {
  color: var(--text-primary);
  font-size: 20px;
  line-height: 1;
}

.records-summary span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.history-search {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 12px;
  color: var(--text-muted);
  background: var(--surface-soft);
  border: 1px solid transparent;
  border-radius: 12px;
  transition: 0.2s ease;
}

.history-search:focus-within {
  color: var(--primary);
  background: #fff;
  border-color: #bfdbfe;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.history-search input {
  width: 100%;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: 0;
}

.history-search button {
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border-radius: 7px;
  cursor: pointer;
}

.history-search button:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.page-size-control {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.page-size-control select {
  min-height: 36px;
  padding: 0 28px 0 10px;
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 9px;
  outline: 0;
  font-weight: 800;
}

.history-list {
  display: grid;
  gap: 16px;
}

.history-card {
  padding: 22px;
  overflow: hidden;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.history-card:hover {
  border-color: #c8d8eb;
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-header {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 16px;
  margin-bottom: 18px;
}

.record-index {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border: 1px solid #dbeafe;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 900;
}

.question-block {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.question-label {
  color: var(--teal);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.question-block strong {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 800;
  line-height: 1.5;
}

.record-time {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-muted);
  font-size: 12.5px;
}

.continue-btn {
  flex: 0 0 auto;
  min-height: 36px;
  font-size: 13.5px;
  border-radius: 8px;
}

.input-tag {
  width: max-content;
  margin-bottom: 14px;
}

.warning {
  display: grid;
  gap: 3px;
  margin-bottom: 16px;
  border-left: 4px solid var(--danger);
  background: var(--danger-soft);
  color: #7f1d1d;
  padding: 12px 16px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14.5px;
  line-height: 1.6;
}

.warning strong {
  font-size: 13px;
}

.answer {
  padding: 18px 20px;
  background: linear-gradient(145deg, #f8fbff, #ffffff 58%);
  border: 1px solid #dfe9f5;
  border-radius: 14px;
}

.answer-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.ai-mark {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: #fff;
  background: linear-gradient(135deg, var(--primary), var(--teal));
  border-radius: 9px;
  font-size: 10px;
  font-weight: 900;
}

.answer h4,
.docs h4 {
  color: var(--primary);
  font-size: 16px;
  font-weight: 800;
}

pre {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: 16px;
  color: var(--text-primary);
  font-family: inherit;
}

.docs {
  margin-top: 18px;
}

.docs h4 {
  margin-bottom: 10px;
}

.doc-item {
  background: var(--surface-soft);
  border: 1px solid var(--border);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  margin-top: 10px;
  font-size: 14.5px;
}

.doc-item span {
  margin-left: 8px;
  font-size: 11px;
  color: #ffffff;
  background: var(--teal);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
}

.feedback {
  display: grid;
  gap: 12px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.pagination-bar > span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
}

.pager-buttons {
  display: flex;
  gap: 6px;
}

.pager-buttons button {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  color: var(--text-secondary);
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 9px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  transition: 0.2s ease;
}

.pager-buttons button:hover:not(:disabled),
.pager-buttons button.active {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.2);
}

.pager-buttons button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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
  color: var(--text-primary);
}

.feedback-title span {
  color: var(--text-muted);
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
  background: var(--surface-soft);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}

.star-rating button.active {
  color: var(--warning);
  background: var(--warning-soft);
  border-color: var(--warning-border);
}

.feedback-submit {
  justify-self: start;
  min-height: 38px;
  padding: 0 16px;
}

@media (max-width: 640px) {
  .page-title {
    padding: 22px;
  }

  .heading-row,
  .pagination-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .heading-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .records-toolbar {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .records-summary {
    padding-right: 0;
    padding-bottom: 12px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .page-size-control {
    justify-content: flex-end;
  }

  .card-header {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .continue-btn {
    grid-column: 1 / -1;
  }

  .feedback-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .pager-buttons {
    justify-content: center;
    overflow-x: auto;
  }
}
</style>
