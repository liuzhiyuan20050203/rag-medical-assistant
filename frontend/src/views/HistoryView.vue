<template>
  <div class="page">
    <div class="page-title ui-page-heading">
      <h2>历史记录</h2>
      <p>
        登录后可查看自己的历史咨询记录。多轮咨询按完整对话展示，旧版单次问答也会合并到同一个列表中。
      </p>
    </div>

    <div v-if="!isLoggedIn" class="login-required ui-empty">
      <strong>登录后查看个人历史记录</strong>
      <span>游客咨询不会显示在个人历史页。登录或注册后，可以查看自己的历史记录。</span>
      <div class="login-actions">
        <RouterLink class="ui-button ui-button--primary" to="/login">
          去登录
        </RouterLink>
        <RouterLink class="ui-button ui-button--soft" to="/register">
          注册账号
        </RouterLink>
      </div>
    </div>

    <div v-if="isLoggedIn" class="toolbar ui-toolbar">
      <button class="ui-button ui-button--primary" @click="loadAllHistory(true)" :disabled="loading">
        {{ loading ? '加载中...' : '刷新历史记录' }}
      </button>
    </div>

    <div v-if="isLoggedIn && !loading && historyItems.length === 0" class="empty-state ui-empty">
      <strong>还没有历史记录</strong>
      <span>完成一次 AI 健康咨询后，系统会在这里保存历史记录。</span>
      <RouterLink class="ui-button ui-button--primary" to="/chat">
        去 AI 助手咨询
      </RouterLink>
    </div>

    <section v-if="isLoggedIn && historyItems.length" class="history-list">
      <article v-for="item in historyItems" :key="item.key" class="history-card ui-card">
        <div class="card-header">
          <div>
            <strong>{{ item.title }}</strong>
            <span>{{ item.time }} · {{ item.summary }}</span>
          </div>

          <div class="card-actions">
            <button
              type="button"
              class="ui-button ui-button--soft"
              @click="toggleItem(item)"
            >
              {{ openedItemKey === item.key ? '收起' : '查看详情' }}
            </button>
            <button
              v-if="item.sessionId"
              type="button"
              class="ui-button ui-button--primary"
              @click="continueConversation(item.sessionId)"
            >
              继续对话
            </button>
          </div>
        </div>

        <div v-if="openedItemKey === item.key" class="detail-box">
          <div v-if="item.type === 'session' && detailLoading" class="loading-text">
            正在加载完整对话...
          </div>
          <div v-else-if="getItemMessages(item).length === 0" class="loading-text">
            暂时没有可展示的消息。
          </div>

          <div
            v-for="message in getItemMessages(item)"
            :key="message.id"
            class="message-row"
            :class="message.role === 'user' ? 'message-row--user' : 'message-row--assistant'"
          >
            <div class="message-role">
              {{ message.role === 'user' ? '我' : 'AI' }}
            </div>
            <div class="message-content">
              <pre>{{ message.content }}</pre>

              <div v-if="message.role === 'assistant' && message.action" class="message-meta">
                <span>{{ actionLabel(message.action) }}</span>
                <span v-if="message.confidence">可靠性 {{ Math.round(message.confidence * 100) }}%</span>
              </div>

              <details
                v-if="message.retrieved_docs && message.retrieved_docs.length"
                class="docs"
              >
                <summary>参考来源（{{ message.retrieved_docs.length }} 条）</summary>
                <div
                  v-for="(doc, index) in message.retrieved_docs"
                  :key="`${message.id}-${index}`"
                  class="doc-item"
                >
                  {{ index + 1 }}. {{ doc.title }}
                  <span>{{ doc.doc_type === 'medicine' ? '药品' : '常见病' }}</span>
                </div>
              </details>
            </div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { cachedGetJson, clearPageCacheByPrefix } from '../api'

const router = useRouter()
const isLoggedIn = ref(false)
const loading = ref(false)
const detailLoading = ref(false)
const sessions = ref([])
const historyRecords = ref([])
const openedItemKey = ref('')
const sessionDetails = ref({})

const formatTime = (value = '') => {
  return String(value || '').replace('T', ' ').slice(0, 19)
}

const displayQuestion = (question = '') => {
  const text = String(question || '').trim()
  const [userText] = text.split('图片识别描述：')
  return userText.replace(/。$/g, '').trim() || text || '未记录问题'
}

const historyItems = computed(() => {
  const sessionIds = new Set(sessions.value.map((item) => Number(item.id)))
  const sessionItems = sessions.value.map((session) => ({
    type: 'session',
    key: `session-${session.id}`,
    id: session.id,
    sessionId: session.id,
    title: session.title || '未命名对话',
    time: formatTime(session.last_message_at || session.updated_at || session.created_at),
    sortTime: session.last_message_at || session.updated_at || session.created_at || '',
    summary: `${session.message_count || 0} 条消息`,
  }))

  const legacyItems = historyRecords.value
    .filter((record) => !record.session_id || !sessionIds.has(Number(record.session_id)))
    .map((record) => ({
      type: 'record',
      key: `record-${record.id}`,
      id: record.id,
      sessionId: record.session_id || null,
      title: displayQuestion(record.question),
      time: formatTime(record.create_time),
      sortTime: record.create_time || '',
      summary: '单次问答',
      record,
    }))

  return [...sessionItems, ...legacyItems].sort((a, b) => String(b.sortTime).localeCompare(String(a.sortTime)))
})

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''
  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

const refreshLoginState = () => {
  isLoggedIn.value = Boolean(localStorage.getItem('ragUser') && localStorage.getItem('ragToken'))
}

const currentUserKey = () => {
  try {
    const raw = localStorage.getItem('ragUser')
    const user = raw ? JSON.parse(raw) : null
    return user?.id || user?.username || 'guest'
  } catch (_error) {
    return 'guest'
  }
}

const historyCacheKey = (name) => `history:unified:${currentUserKey()}:${name}`

const sessionDetailCacheKey = (sessionId) => `history:session:${currentUserKey()}:${sessionId}`

const actionLabel = (action = '') => {
  const labels = {
    danger_alert: '危险症状提醒',
    ask_followup: '追问补充信息',
    medicine_query: '药品查询',
    rag_answer: '健康问答',
    image_assist: '图片/视频辅助分析',
  }
  return labels[action] || action
}

const fetchCachedJson = async (key, url, force = false) => {
  return cachedGetJson(key, url, {
    force,
    timeoutMs: 15000,
    fetchOptions: {
      headers: authHeaders(),
    },
  })
}

const loadAllHistory = async (force = false) => {
  refreshLoginState()
  if (!isLoggedIn.value) {
    sessions.value = []
    historyRecords.value = []
    return
  }

  loading.value = true
  try {
    if (force) {
      clearPageCacheByPrefix(`history:unified:${currentUserKey()}:`)
      clearPageCacheByPrefix(`history:session:${currentUserKey()}:`)
      sessionDetails.value = {}
    }

    const [sessionData, historyData] = await Promise.all([
      fetchCachedJson(historyCacheKey('sessions'), '/api/conversations/sessions', force),
      fetchCachedJson(historyCacheKey('records'), '/api/history/list', force),
    ])

    sessions.value = sessionData.data || []
    historyRecords.value = historyData.data || []
  } catch (error) {
    alert('加载历史记录失败，请检查后端服务是否正常运行。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadSessionDetail = async (sessionId) => {
  if (sessionDetails.value[sessionId]) return

  detailLoading.value = true
  try {
    const data = await fetchCachedJson(
      sessionDetailCacheKey(sessionId),
      `/api/conversations/${sessionId}`,
    )
    sessionDetails.value = {
      ...sessionDetails.value,
      [sessionId]: data.data || { messages: [] },
    }
  } catch (error) {
    alert('加载完整对话失败，请稍后重试。')
    console.error(error)
  } finally {
    detailLoading.value = false
  }
}

const recordMessages = (record) => [
  {
    id: `record-${record.id}-user`,
    role: 'user',
    content: record.question || '',
  },
  {
    id: `record-${record.id}-assistant`,
    role: 'assistant',
    content: record.answer || '',
    action: record.agent_meta?.action || '',
    confidence: record.agent_meta?.confidence || null,
    retrieved_docs: record.retrieved_docs || [],
  },
]

const getItemMessages = (item) => {
  if (item.type === 'record') {
    return recordMessages(item.record)
  }

  return sessionDetails.value[item.sessionId]?.messages || []
}

const toggleItem = async (item) => {
  if (openedItemKey.value === item.key) {
    openedItemKey.value = ''
    return
  }

  openedItemKey.value = item.key
  if (item.type === 'session') {
    await loadSessionDetail(item.sessionId)
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

onMounted(() => {
  refreshLoginState()
  if (isLoggedIn.value) {
    loadAllHistory()
  }
})
</script>

<style scoped>
.login-required,
.empty-state {
  display: grid;
  justify-items: start;
  gap: 12px;
}

.login-required strong,
.empty-state strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.login-required span,
.empty-state span {
  color: var(--text-muted);
  line-height: 1.7;
}

.login-actions,
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.history-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.history-card {
  padding: 18px;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-header > div:first-child {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.card-header strong {
  color: var(--text-primary);
  font-size: 17px;
}

.card-header span,
.loading-text {
  color: var(--text-muted);
  font-size: 14px;
}

.detail-box {
  display: grid;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.message-row {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 10px;
}

.message-role {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  color: var(--surface);
  background: var(--medical-blue);
  border-radius: var(--radius-pill);
  font-size: 14px;
  font-weight: 900;
}

.message-row--user .message-role {
  background: var(--medicine-amber);
}

.message-content {
  padding: 12px;
  background: #fbfdff;
  border: 1px solid #e4edf3;
  border-radius: var(--radius-sm);
}

.message-row--user .message-content {
  background: #fffaf0;
  border-color: #fde7bd;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  color: var(--text-secondary);
  font-family: "Microsoft YaHei", Arial, sans-serif;
  font-size: 15px;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.message-meta span {
  color: var(--medical-blue);
  background: var(--info-soft);
  border: 1px solid var(--info-border);
  border-radius: var(--radius-pill);
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 800;
}

.docs {
  margin-top: 10px;
}

.docs summary {
  color: var(--text-secondary);
  cursor: pointer;
  font-weight: 900;
}

.doc-item {
  margin-top: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.doc-item span {
  margin-left: 8px;
  color: var(--surface);
  background: var(--medical-blue);
  border-radius: var(--radius-pill);
  padding: 2px 7px;
  font-size: 12px;
}

@media (max-width: 640px) {
  .card-header {
    flex-direction: column;
  }

  .message-row {
    grid-template-columns: 1fr;
  }
}
</style>
