<template>
  <div v-if="!isAdmin" class="access-gate">
    <p class="eyebrow">ADMIN ONLY</p>
    <h2>需要管理员登录</h2>
    <p>管理员后台包含知识库写入、向量索引更新和问答审核操作，请先使用管理员账号登录。</p>
    <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
    <RouterLink to="/login">去登录</RouterLink>
  </div>

  <div v-else class="admin-page">
    <section class="admin-hero">
      <div>
        <p class="eyebrow">ADMIN CONSOLE</p>
        <h2>管理员后台</h2>
        <p>
          管理疾病知识文档、药品说明书和用户问答记录，并在知识更新后重建 RAG 向量索引。
        </p>
      </div>

      <div class="admin-actions">
        <button type="button" @click="loadAdminData(true)" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新数据' }}
        </button>
        <button class="index-btn" type="button" @click="rebuildIndex" :disabled="indexLoading">
          {{ indexLoading ? '更新中...' : '更新向量索引' }}
        </button>
      </div>
    </section>

    <section class="metric-grid">
      <article>
        <strong>{{ users.length }}</strong>
        <span>系统用户</span>
      </article>
      <article>
        <strong>{{ knowledge.knowledge.disease_count }}</strong>
        <span>疾病知识</span>
      </article>
      <article>
        <strong>{{ knowledge.knowledge.medicine_count }}</strong>
        <span>药品说明</span>
      </article>
      <article>
        <strong>{{ knowledge.knowledge.warning_rule_count }}</strong>
        <span>危险规则</span>
      </article>
      <article>
        <strong>{{ historyList.length }}</strong>
        <span>问答记录</span>
      </article>
    </section>

    <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>

    <section class="agent-log-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">AGENT OBSERVABILITY</p>
          <h3>会话与 Agent 调度日志</h3>
        </div>
      </div>

      <div class="agent-log-grid">
        <article>
          <div class="mini-heading">
            <strong>最近会话</strong>
            <span>{{ conversationSessions.length }} 条</span>
          </div>

          <div v-if="conversationSessions.length === 0" class="empty-state">
            暂无多轮会话记录。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in conversationSessions.slice(0, 6)" :key="item.id" class="mini-row">
              <strong>{{ item.title }}</strong>
              <span>会话 #{{ item.id }} · 消息 {{ item.message_count }} · 用户 {{ item.user_id || '未登录' }}</span>
            </div>
          </div>
        </article>

        <article>
          <div class="mini-heading">
            <strong>最近 Agent 运行</strong>
            <span>{{ agentRuns.length }} 条</span>
          </div>

          <div v-if="agentRuns.length === 0" class="empty-state">
            暂无 Agent 调度日志。
          </div>

          <div v-else class="mini-list">
            <div v-for="item in agentRuns.slice(0, 6)" :key="item.id" class="mini-row">
              <strong>{{ labelAction(item.action) }} / {{ labelIntent(item.intent) }}</strong>
              <span>
                运行 #{{ item.id }} · 会话 #{{ item.session_id }} · 可靠性 {{ Math.round((item.confidence || 0) * 100) }}%
              </span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="review-workbench">
      <div class="section-title">
        <div>
          <p class="eyebrow">KNOWLEDGE GAP REVIEW</p>
          <h3>待补充知识库 / 错误样本</h3>
          <span class="section-help">
            自动汇总低可靠性、药品库缺失、图片待复核和用户差评样本，用于定位知识库缺口。
          </span>
        </div>

        <div class="tabs">
          <button
            v-for="filter in reviewFilters"
            :key="filter.value"
            type="button"
            :class="{ active: activeReviewFilter === filter.value }"
            @click="activeReviewFilter = filter.value"
          >
            {{ filter.label }}
          </button>
        </div>
      </div>

      <div class="review-summary">
        <article>
          <strong>{{ pendingIssues.length }}</strong>
          <span>待处理</span>
        </article>
        <article>
          <strong>{{ issueTypeCount('药品库缺失') }}</strong>
          <span>药品库缺失</span>
        </article>
        <article>
          <strong>{{ issueTypeCount('RAG低命中') }}</strong>
          <span>RAG低命中</span>
        </article>
        <article>
          <strong>{{ issueTypeCount('图片识别待复核') }}</strong>
          <span>图片复核</span>
        </article>
      </div>

      <div v-if="filteredIssues.length === 0" class="empty-state">
        当前筛选下暂无待处理样本。
      </div>

      <div v-else class="issue-list">
        <article v-for="item in filteredIssues" :key="item.record_id" class="issue-card">
          <div class="issue-head">
            <div>
              <span :class="['issue-tag', issueTagClass(item.issue_type)]">
                {{ item.issue_type }}
              </span>
              <strong>{{ item.keyword || '待补充条目' }}</strong>
            </div>
            <small>{{ item.create_time }}</small>
          </div>

          <p class="issue-question">{{ item.question }}</p>

          <div class="issue-meta">
            <span>可靠性：{{ Math.round((item.confidence || 0) * 100) }}%</span>
            <span>检索数：{{ item.retrieved_count }}</span>
            <span>最高分：{{ item.top_score }}</span>
            <span v-if="item.rating">评分：{{ item.rating }} 星</span>
            <span v-if="item.action">动作：{{ labelAction(item.action) }}</span>
          </div>

          <p class="issue-fix">{{ item.suggested_fix }}</p>
          <p v-if="item.feedback_text" class="feedback-note">用户反馈：{{ item.feedback_text }}</p>
          <p v-if="item.error_reason" class="feedback-note">管理员标注：{{ item.error_reason }}</p>

          <div class="issue-actions">
            <button
              type="button"
              class="draft-btn"
              @click="fillKnowledgeDraft(item, item.suggested_category === 'medicine' ? 'medicine' : 'disease')"
            >
              {{ item.suggested_category === 'medicine' ? '生成药品库草稿' : '生成疾病库草稿' }}
            </button>
            <button
              v-if="activeReviewFilter !== 'all'"
              type="button"
              class="ghost-btn"
              @click="showAllIssues"
            >
              查看全部
            </button>
            <button v-else type="button" class="ghost-btn" @click="loadReviewIssues">
              刷新样本
            </button>
          </div>
        </article>
      </div>
    </section>

    <section class="user-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">USER PERMISSIONS</p>
          <h3>用户权限管理</h3>
        </div>
      </div>

      <form class="user-create" @submit.prevent="createSystemUser">
        <label>
          用户名
          <input v-model="userForm.username" placeholder="至少 3 位" />
        </label>

        <label>
          初始密码
          <input v-model="userForm.password" type="password" placeholder="至少 6 位" />
        </label>

        <label>
          角色权限
          <select v-model="userForm.role">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </label>

        <label class="checkbox-label">
          <input v-model="userForm.active" type="checkbox" />
          启用账号
        </label>

        <button type="submit" :disabled="userSaving">
          {{ userSaving ? '创建中...' : '创建用户' }}
        </button>
      </form>

      <div class="user-table">
        <article v-for="item in users" :key="item.username" class="user-row">
          <div>
            <strong>{{ item.username }}</strong>
            <span>{{ item.create_time }}</span>
          </div>

          <select v-model="userEdits[item.username].role">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>

          <label class="checkbox-label compact">
            <input v-model="userEdits[item.username].active" type="checkbox" />
            启用
          </label>

          <input
            v-model="userEdits[item.username].password"
            type="password"
            placeholder="新密码，不填则不改"
          />

          <div class="user-actions">
            <button type="button" @click="updateSystemUser(item.username)">
              保存
            </button>
            <button
              class="delete-user"
              type="button"
              @click="deleteSystemUser(item.username)"
              :disabled="item.username === user?.username"
            >
              删除
            </button>
          </div>
        </article>
      </div>
    </section>

    <section ref="uploadSectionRef" class="upload-grid" aria-label="知识文档上传">
      <article class="upload-card">
        <div class="card-heading">
          <span>01</span>
          <div>
            <h3>上传疾病知识文档</h3>
            <p>支持 JSON 结构化知识，或上传普通文本生成一条可检索疾病知识。</p>
          </div>
        </div>

        <input type="file" accept=".txt,.json,.md" @change="handleFile($event, 'disease')" />
        <textarea
          v-model="uploads.disease.content"
          placeholder="可粘贴疾病知识 JSON 或纯文本，例如：疾病名称、症状、护理建议、用药注意、就医提醒。"
        ></textarea>

        <button type="button" @click="uploadDoc('disease')" :disabled="uploads.disease.loading">
          {{ uploads.disease.loading ? '上传中...' : '写入疾病知识库' }}
        </button>
        <small v-if="uploads.disease.message">{{ uploads.disease.message }}</small>
        <div v-if="uploads.disease.result" class="upload-result">
          <div class="upload-summary">
            <span>新增 {{ uploads.disease.result.summary.created }}</span>
            <span>更新 {{ uploads.disease.result.summary.updated }}</span>
            <span>疑似重复 {{ uploads.disease.result.summary.similar }}</span>
          </div>

          <article v-for="item in uploads.disease.result.data" :key="item.name" class="upload-row">
            <strong>{{ item.name }}</strong>
            <span :class="['upload-status', item.status]">
              {{ item.status === 'created' ? '新增' : '更新已有' }}
            </span>
            <p v-if="item.duplicate_of">同名记录：{{ item.duplicate_of.name }}，本次已覆盖更新。</p>
            <p v-if="item.similar_duplicates?.length">
              疑似重复：{{ item.similar_duplicates.map((dup) => dup.name).join('、') }}
            </p>
          </article>
        </div>
      </article>

      <article class="upload-card">
        <div class="card-heading">
          <span>02</span>
          <div>
            <h3>上传药品说明书</h3>
            <p>支持 JSON 结构化药品字段，也可以从说明书文本中抽取适用、禁忌和不良反应。</p>
          </div>
        </div>

        <input type="file" accept=".txt,.json,.md" @change="handleFile($event, 'medicine')" />
        <textarea
          v-model="uploads.medicine.content"
          placeholder="可粘贴药品说明书 JSON 或纯文本，例如：适应症、注意事项、禁忌、不良反应。"
        ></textarea>

        <button type="button" @click="uploadDoc('medicine')" :disabled="uploads.medicine.loading">
          {{ uploads.medicine.loading ? '上传中...' : '写入药品知识库' }}
        </button>
        <small v-if="uploads.medicine.message">{{ uploads.medicine.message }}</small>
        <div v-if="uploads.medicine.result" class="upload-result">
          <div class="upload-summary">
            <span>新增 {{ uploads.medicine.result.summary.created }}</span>
            <span>更新 {{ uploads.medicine.result.summary.updated }}</span>
            <span>疑似重复 {{ uploads.medicine.result.summary.similar }}</span>
          </div>

          <article v-for="item in uploads.medicine.result.data" :key="item.name" class="upload-row">
            <strong>{{ item.name }}</strong>
            <span :class="['upload-status', item.status]">
              {{ item.status === 'created' ? '新增' : '更新已有' }}
            </span>
            <p v-if="item.duplicate_of">同名记录：{{ item.duplicate_of.name }}，本次已覆盖更新。</p>
            <p v-if="item.similar_duplicates?.length">
              疑似重复：{{ item.similar_duplicates.map((dup) => dup.name).join('、') }}
            </p>
          </article>
        </div>
      </article>
    </section>

    <section class="delete-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">KNOWLEDGE DELETE</p>
          <h3>搜索并删除知识</h3>
        </div>
      </div>

      <form class="delete-search" @submit.prevent="searchDeleteCandidates">
        <select v-model="deleteTool.kind">
          <option value="disease">疾病知识</option>
          <option value="medicine">药品说明</option>
        </select>
        <input v-model="deleteTool.keyword" placeholder="输入名称、症状、分类或适用情况关键词" />
        <button type="submit" :disabled="deleteTool.loading">
          {{ deleteTool.loading ? '搜索中...' : '搜索' }}
        </button>
      </form>

      <p v-if="deleteTool.message" class="delete-message">{{ deleteTool.message }}</p>

      <div v-if="deleteTool.results.length" class="delete-list">
        <article v-for="item in deleteTool.results" :key="`${deleteTool.kind}-${item.id}`" class="delete-card">
          <div>
            <strong>{{ item.name }}</strong>
            <span>{{ deleteTool.kind === 'disease' ? item.category : item.type }}</span>
          </div>
          <p>{{ deleteTool.kind === 'disease' ? item.description : item.usage }}</p>
          <button type="button" class="delete-knowledge" @click="deleteKnowledgeItem(item)">
            删除
          </button>
        </article>
      </div>
    </section>

    <section class="admin-grid">
      <article class="knowledge-panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">KNOWLEDGE BASE</p>
            <h3>查看知识库</h3>
          </div>

          <div class="tabs">
            <button
              type="button"
              :class="{ active: activeKnowledge === 'disease' }"
              @click="activeKnowledge = 'disease'"
            >
              疾病
            </button>
            <button
              type="button"
              :class="{ active: activeKnowledge === 'medicine' }"
              @click="activeKnowledge = 'medicine'"
            >
              药品
            </button>
            <button
              type="button"
              :class="{ active: activeKnowledge === 'warning' }"
              @click="activeKnowledge = 'warning'"
            >
              规则
            </button>
          </div>
        </div>

        <div class="knowledge-list">
          <article
            v-for="item in visibleKnowledge"
            :key="knowledgeKey(item)"
            class="knowledge-item"
          >
            <template v-if="activeKnowledge === 'disease'">
              <strong>{{ item.name }}</strong>
              <span>{{ item.category }}</span>
              <p>{{ item.symptoms?.join('、') }}</p>
            </template>

            <template v-else-if="activeKnowledge === 'medicine'">
              <strong>{{ item.name }}</strong>
              <span>{{ item.type }}</span>
              <p>{{ item.usage }}</p>
            </template>

            <template v-else>
              <strong>{{ item }}</strong>
              <p>命中后优先返回就医提醒</p>
            </template>
          </article>
        </div>
      </article>

      <article class="history-panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">ANSWER REVIEW</p>
            <h3>用户问答记录</h3>
          </div>
        </div>

        <div v-if="historyList.length === 0" class="empty-state">
          暂无问答记录。
        </div>

        <div v-else class="review-list">
          <article v-for="item in historyList" :key="item.id" class="review-card">
            <div class="review-header">
              <strong>{{ item.question }}</strong>
              <span>{{ item.create_time }}</span>
            </div>

            <pre>{{ item.answer }}</pre>

            <div class="review-meta">
              <span v-if="item.warning?.has_warning" class="danger-tag">危险提醒</span>
              <span v-if="item.is_error" class="error-tag">已标记错误</span>
              <span v-if="item.rating">用户评分：{{ item.rating }} 星</span>
            </div>

            <p v-if="item.feedback_text" class="feedback-note">
              详细评价：{{ item.feedback_text }}
            </p>

            <div class="mark-row">
              <input
                v-model="errorReasons[item.id]"
                placeholder="错误原因，例如：知识库不足、回答不准确"
              />
              <button type="button" @click="markError(item.id)">
                标记错误回答
              </button>
            </div>
          </article>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import {
  apiUrl,
  clearPageCache,
  clearPageCacheByPrefix,
  readPageCache,
  writePageCache,
} from '../api'

const user = ref(null)
const loading = ref(false)
const indexLoading = ref(false)
const statusMessage = ref('')
const historyList = ref([])
const issueList = ref([])
const conversationSessions = ref([])
const agentRuns = ref([])
const users = ref([])
const userSaving = ref(false)
const activeKnowledge = ref('disease')
const activeReviewFilter = ref('needs_review')
const uploadSectionRef = ref(null)
const errorReasons = reactive({})
const userEdits = reactive({})

const reviewFilters = [
  { label: '待处理', value: 'needs_review' },
  { label: '药品库缺失', value: 'medicine' },
  { label: 'RAG低命中', value: 'rag' },
  { label: '图片复核', value: 'image' },
  { label: '差评/标错', value: 'bad' },
  { label: '全部', value: 'all' },
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

const labelAction = (action) => actionLabels[action] || action || '未判断'

const labelIntent = (intent) => intentLabels[intent] || intent || '未识别'

const userForm = reactive({
  username: '',
  password: '',
  role: 'user',
  active: true,
})

const knowledge = ref({
  knowledge: {
    disease_count: 0,
    medicine_count: 0,
    warning_rule_count: 0,
    total_knowledge_count: 0,
  },
  diseases: [],
  medicines: [],
  warning_rules: [],
})

const uploads = reactive({
  disease: {
    fileName: '',
    content: '',
    loading: false,
    message: '',
    result: null,
  },
  medicine: {
    fileName: '',
    content: '',
    loading: false,
    message: '',
    result: null,
  },
})

const deleteTool = reactive({
  kind: 'medicine',
  keyword: '',
  loading: false,
  message: '',
  results: [],
})

const isAdmin = computed(() => user.value?.role === 'admin')

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

const clearStaleAdminSession = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  user.value = null
  window.dispatchEvent(new Event('rag-user-change'))
}

const parseAdminResponse = async (response) => {
  if (response.status === 401 || response.status === 403) {
    statusMessage.value = '管理员登录已失效或权限不足，请重新登录管理员账号。'
    clearStaleAdminSession()
    const error = new Error('admin forbidden')
    error.expectedAuthFailure = true
    throw error
  }

  return response.json()
}

const adminCachePrefix = () => `admin:${user.value?.id || user.value?.username || 'guest'}:`

const adminCacheKey = (name) => `${adminCachePrefix()}${name}`

const cachedAdminGet = async (name, path, force = false) => {
  const key = adminCacheKey(name)
  const cached = force ? null : readPageCache(key)

  if (cached) {
    return cached
  }

  const response = await fetch(apiUrl(path), {
    headers: authHeaders(),
  })
  const data = await parseAdminResponse(response)
  return writePageCache(key, data)
}

const clearAdminDataCache = () => {
  clearPageCacheByPrefix(adminCachePrefix())
  clearPageCacheByPrefix('knowledge:')
  clearPageCache('home:stats')
  clearPageCache('analytics:summary')
}

const visibleKnowledge = computed(() => {
  if (activeKnowledge.value === 'disease') {
    return knowledge.value.diseases
  }

  if (activeKnowledge.value === 'medicine') {
    return knowledge.value.medicines
  }

  return knowledge.value.warning_rules
})

const pendingIssues = computed(() => issueList.value.filter((item) => item.needs_review))

const filteredIssues = computed(() => {
  const list = issueList.value

  if (activeReviewFilter.value === 'needs_review') {
    return list.filter((item) => item.needs_review)
  }

  if (activeReviewFilter.value === 'medicine') {
    return list.filter((item) => item.issue_type === '药品库缺失')
  }

  if (activeReviewFilter.value === 'rag') {
    return list.filter((item) => item.issue_type === 'RAG低命中')
  }

  if (activeReviewFilter.value === 'image') {
    return list.filter((item) => item.issue_type === '图片识别待复核')
  }

  if (activeReviewFilter.value === 'bad') {
    return list.filter((item) => item.is_error || item.rating === 1 || item.rating === 2)
  }

  return list
})

const issueTypeCount = (type) => issueList.value.filter((item) => item.issue_type === type).length

const knowledgeKey = (item) => {
  if (typeof item === 'string') {
    return item
  }

  return `${item.name}-${item.type || item.category || ''}`
}

const loadUser = () => {
  const raw = localStorage.getItem('ragUser')
  user.value = raw ? JSON.parse(raw) : null
}

const syncUserEdits = () => {
  users.value.forEach((item) => {
    userEdits[item.username] = {
      role: item.role || 'user',
      active: item.active !== false,
      password: '',
    }
  })
}

const loadAdminData = async (force = false) => {
  if (!isAdmin.value) {
    return
  }

  loading.value = true
  statusMessage.value = ''

  try {
    const [knowledgeData, historyData, usersData, issuesData, sessionsData, runsData] = await Promise.all([
      cachedAdminGet('knowledge', '/api/admin/knowledge', force),
      cachedAdminGet('history', '/api/admin/history', force),
      cachedAdminGet('users', '/api/admin/users', force),
      cachedAdminGet('issues', '/api/admin/review/issues', force),
      cachedAdminGet('sessions', '/api/admin/conversations/sessions', force),
      cachedAdminGet('runs', '/api/admin/agent/runs', force),
    ])

    knowledge.value = knowledgeData
    historyList.value = historyData.data || []
    users.value = usersData.data || []
    issueList.value = issuesData.data || []
    conversationSessions.value = sessionsData.data || []
    agentRuns.value = runsData.data || []
    syncUserEdits()
  } catch (error) {
    if (!error.expectedAuthFailure) {
      console.error(error)
    }
    if (!statusMessage.value) {
      statusMessage.value = '后台数据加载失败，请检查后端服务是否正常运行。'
    }
  } finally {
    loading.value = false
  }
}

const createSystemUser = async () => {
  userSaving.value = true
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl('/api/admin/users'), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(userForm),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message

    if (data.success) {
      userForm.username = ''
      userForm.password = ''
      userForm.role = 'user'
      userForm.active = true
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户创建失败。'
    }
  } finally {
    userSaving.value = false
  }
}

const updateSystemUser = async (username) => {
  const edit = userEdits[username]
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(username)}`), {
      method: 'PUT',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(edit),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message
    clearAdminDataCache()
    await loadAdminData(true)
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户更新失败。'
    }
  }
}

const deleteSystemUser = async (username) => {
  if (!confirm(`确定删除用户 ${username} 吗？`)) {
    return
  }

  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/users/${encodeURIComponent(username)}`), {
      method: 'DELETE',
      headers: authHeaders(),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message
    clearAdminDataCache()
    await loadAdminData(true)
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '用户删除失败。'
    }
  }
}

const handleFile = (event, kind) => {
  const file = event.target.files?.[0]

  if (!file) {
    return
  }

  uploads[kind].fileName = file.name
  uploads[kind].message = `已选择：${file.name}`
  uploads[kind].result = null

  const reader = new FileReader()
  reader.onload = () => {
    uploads[kind].content = String(reader.result || '')
  }
  reader.readAsText(file, 'utf-8')
}

const issueTagClass = (type) => {
  if (type === '药品库缺失') return 'medicine'
  if (type === '图片识别待复核') return 'image'
  if (type === '用户差评/已标错') return 'bad'
  if (type === 'RAG低命中') return 'rag'
  return 'neutral'
}

const scrollToUploadSection = async () => {
  await nextTick()
  uploadSectionRef.value?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

const showAllIssues = () => {
  activeReviewFilter.value = 'all'
  statusMessage.value = '已切换为查看全部待复核样本。'
}

const loadReviewIssues = async () => {
  statusMessage.value = '正在刷新待复核样本...'

  try {
    const data = await cachedAdminGet('issues', '/api/admin/review/issues', true)
    issueList.value = data.data || []
    statusMessage.value = '待复核样本已刷新。'
  } catch (error) {
    console.error(error)
    if (!statusMessage.value) {
      statusMessage.value = '待复核样本刷新失败。'
    }
  }
}

const fillKnowledgeDraft = async (item, kind) => {
  const keyword = item.keyword || '待补充条目'

  if (kind === 'medicine') {
    uploads.medicine.fileName = `${keyword}-medicine-draft.json`
    uploads.medicine.content = JSON.stringify(
      {
        name: keyword,
        type: '待补充药品类别',
        usage: `根据用户问题补充：${item.question}`,
        notice: '请根据药品说明书补充注意事项。',
        contraindication: '请根据药品说明书补充禁忌人群。',
        side_effect: '请根据药品说明书补充不良反应。',
        source: '管理员根据低置信度样本补充',
      },
      null,
      2,
    )
    uploads.medicine.message = '已生成药品库草稿，请核对说明书后写入。'
    activeKnowledge.value = 'medicine'
    statusMessage.value = '药品库草稿已生成，已定位到下方上传区域，请核对后写入。'
    await scrollToUploadSection()
    return
  }

  uploads.disease.fileName = `${keyword}-disease-draft.json`
  uploads.disease.content = JSON.stringify(
    {
      name: keyword,
      category: '待补充分类',
      symptoms: ['待补充症状'],
      description: `根据用户问题补充：${item.question}`,
      care_advice: '请补充家庭护理和观察建议。',
      medicine_notice: '请补充用药注意，避免直接替代医生诊断。',
      warning: '请补充需要及时就医的危险信号。',
      source: '管理员根据低置信度样本补充',
    },
    null,
    2,
  )
  uploads.disease.message = '已生成疾病库草稿，请补全并核对后写入。'
  activeKnowledge.value = 'disease'
  statusMessage.value = '疾病知识草稿已生成，已定位到下方上传区域，请核对后写入。'
  await scrollToUploadSection()
}

const uploadDoc = async (kind) => {
  const target = uploads[kind]

  if (!target.content.trim()) {
    target.message = '请先选择文件或粘贴文档内容。'
    return
  }

  target.loading = true
  target.message = ''
  target.result = null

  try {
    const response = await fetch(apiUrl(`/api/admin/upload/${kind}`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        file_name: target.fileName || `${kind}-manual-input.txt`,
        content: target.content,
      }),
    })

    const data = await parseAdminResponse(response)
    target.message = data.message
    target.result = data.success
      ? {
          summary: data.summary || { created: 0, updated: 0, similar: 0 },
          data: data.data || [],
        }
      : null

    if (data.success) {
      target.content = ''
      target.fileName = ''
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    target.message = '上传失败，请检查后端服务是否正常运行。'
  } finally {
    target.loading = false
  }
}

const searchDeleteCandidates = async () => {
  if (!deleteTool.keyword.trim()) {
    deleteTool.message = '请输入要搜索的关键词。'
    deleteTool.results = []
    return
  }

  deleteTool.loading = true
  deleteTool.message = ''
  deleteTool.results = []

  try {
    const response = await fetch(apiUrl('/api/admin/knowledge/search'), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        kind: deleteTool.kind,
        keyword: deleteTool.keyword,
      }),
    })

    const data = await parseAdminResponse(response)
    deleteTool.message = data.message
    deleteTool.results = data.data || []
  } catch (error) {
    console.error(error)
    deleteTool.message = '搜索失败，请检查后端服务是否正常运行。'
  } finally {
    deleteTool.loading = false
  }
}

const deleteKnowledgeItem = async (item) => {
  const kindLabel = deleteTool.kind === 'disease' ? '疾病知识' : '药品说明'

  if (!confirm(`确定删除${kindLabel}“${item.name}”吗？删除后需要更新向量索引。`)) {
    return
  }

  deleteTool.loading = true
  deleteTool.message = ''

  try {
    const response = await fetch(apiUrl(`/api/admin/knowledge/${deleteTool.kind}/${item.id}`), {
      method: 'DELETE',
      headers: authHeaders(),
    })

    const data = await parseAdminResponse(response)
    deleteTool.message = data.message

    if (data.success) {
      deleteTool.results = deleteTool.results.filter((candidate) => candidate.id !== item.id)
      statusMessage.value = '知识已删除。请点击“更新向量索引”，同步 RAG 检索结果。'
      clearAdminDataCache()
      await loadAdminData(true)
    }
  } catch (error) {
    console.error(error)
    deleteTool.message = '删除失败，请检查后端服务是否正常运行。'
  } finally {
    deleteTool.loading = false
  }
}

const rebuildIndex = async () => {
  indexLoading.value = true
  statusMessage.value = ''

  try {
    const response = await fetch(apiUrl('/api/admin/vector/rebuild'), {
      method: 'POST',
      headers: authHeaders(),
    })
    const data = await parseAdminResponse(response)
    const indexData = data.data || {}
    const modeLabel = indexData.index_mode === 'semantic' ? '语义向量检索' : '关键词检索'
    const modelText = indexData.embedding_model ? `，模型：${indexData.embedding_model}` : ''
    const fallbackText = indexData.fallback ? `，${indexData.fallback_reason}` : ''
    statusMessage.value = `${data.message}，模式：${modeLabel}${modelText}，文档数：${indexData.doc_count}，向量维度：${indexData.dimension}${fallbackText}`
  } catch (error) {
    console.error(error)
    statusMessage.value = '向量索引更新失败，请检查后端服务是否正常运行。'
  } finally {
    indexLoading.value = false
  }
}

const markError = async (recordId) => {
  try {
    const response = await fetch(apiUrl(`/api/admin/history/${recordId}/mark-error`), {
      method: 'POST',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        reason: errorReasons[recordId] || '',
      }),
    })

    const data = await parseAdminResponse(response)
    statusMessage.value = data.message
    clearAdminDataCache()
    await loadAdminData(true)
  } catch (error) {
    console.error(error)
    statusMessage.value = '标记失败，请检查后端服务是否正常运行。'
  }
}

onMounted(() => {
  loadUser()
  loadAdminData()
})
</script>

<style scoped>
.admin-page {
  display: grid;
  gap: 24px;
}

.access-gate,
.admin-hero,
.agent-log-panel,
.review-workbench,
.user-panel,
.delete-panel,
.upload-card,
.knowledge-panel,
.history-panel {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.access-gate {
  display: grid;
  gap: 12px;
  max-width: 720px;
  padding: 36px;
}

.access-gate h2,
.admin-hero h2 {
  color: var(--text-primary);
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 900;
  line-height: 1.15;
}

.access-gate p,
.admin-hero p,
.upload-card p {
  color: var(--text-secondary);
  line-height: 1.85;
}

.access-gate a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: max-content;
  min-height: 42px;
  padding: 0 18px;
  color: #ffffff;
  text-decoration: none;
  background: var(--medical-blue);
  border-radius: 8px;
  font-weight: 900;
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.admin-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: clamp(24px, 4vw, 40px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.88)),
    #ffffff;
}

.admin-hero p {
  max-width: 720px;
  margin-top: 12px;
}

.admin-actions,
.tabs,
.mark-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

button {
  min-height: 42px;
  padding: 0 16px;
  color: #ffffff;
  background: var(--medical-blue);
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
}

button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.index-btn {
  background: var(--pharmacy-teal);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.metric-grid article {
  min-height: 108px;
  padding: 20px;
  text-align: center;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.metric-grid strong {
  display: block;
  color: var(--medical-blue);
  font-size: 31px;
  font-weight: 900;
  line-height: 1.15;
}

.metric-grid span {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-weight: 800;
}

.status-message {
  padding: 13px 16px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-weight: 800;
}

.agent-log-panel {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.agent-log-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.agent-log-grid > article {
  display: grid;
  gap: 12px;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.mini-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.mini-heading strong {
  color: var(--text-primary);
  font-weight: 900;
}

.mini-heading span {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 900;
}

.mini-list {
  display: grid;
  gap: 8px;
}

.mini-row {
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.mini-row strong,
.mini-row span {
  display: block;
}

.mini-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.mini-row span {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.review-workbench {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.review-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.review-summary article {
  padding: 14px 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.review-summary strong,
.review-summary span {
  display: block;
}

.review-summary strong {
  color: var(--medical-blue);
  font-size: 26px;
  font-weight: 900;
  line-height: 1.15;
}

.review-summary span {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 900;
}

.issue-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.issue-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.issue-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.issue-head > div {
  display: grid;
  gap: 8px;
}

.issue-head strong {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.issue-head small {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-weight: 800;
}

.issue-tag {
  width: max-content;
  padding: 4px 9px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.issue-tag.medicine {
  color: #92400e;
  background: #fffbeb;
}

.issue-tag.rag {
  color: #075985;
  background: #eff6ff;
}

.issue-tag.image {
  color: #166534;
  background: #f0fdf4;
}

.issue-tag.bad {
  color: #991b1b;
  background: #fef2f2;
}

.issue-question,
.issue-fix {
  color: var(--text-secondary);
  line-height: 1.7;
}

.issue-question {
  padding: 10px 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.issue-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.issue-meta span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.issue-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.draft-btn {
  background: var(--pharmacy-teal);
}

.ghost-btn {
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
}

.upload-grid,
.admin-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.delete-panel {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.delete-search {
  display: grid;
  grid-template-columns: 160px minmax(220px, 1fr) auto;
  gap: 12px;
}

.delete-message {
  padding: 10px 12px;
  color: #075985;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-weight: 800;
}

.delete-list {
  display: grid;
  gap: 10px;
}

.delete-card {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) minmax(240px, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.delete-card strong,
.delete-card span {
  display: block;
}

.delete-card strong {
  color: var(--text-primary);
  font-weight: 900;
}

.delete-card span {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.delete-card p {
  max-height: 72px;
  overflow: auto;
  color: var(--text-secondary);
  line-height: 1.65;
}

.delete-knowledge {
  background: var(--danger);
}

.user-panel {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.user-create {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) minmax(150px, 1fr) 150px 120px auto;
  gap: 12px;
  align-items: end;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.user-create label,
.checkbox-label {
  display: grid;
  gap: 7px;
  color: var(--text-primary);
  font-weight: 900;
}

.checkbox-label {
  display: flex;
  align-items: center;
  min-height: 42px;
  color: var(--text-secondary);
}

.checkbox-label input {
  width: 16px;
  min-height: 16px;
}

.checkbox-label.compact {
  justify-content: center;
}

.user-table {
  display: grid;
  gap: 10px;
}

.user-row {
  display: grid;
  grid-template-columns: minmax(150px, 1.1fr) 140px 90px minmax(180px, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.user-row strong,
.user-row span {
  display: block;
}

.user-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.user-row span {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.user-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.delete-user {
  background: var(--danger);
}

.upload-card {
  display: grid;
  gap: 16px;
  padding: 22px;
}

.card-heading,
.section-title,
.review-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.card-heading {
  align-items: flex-start;
}

.card-heading > span {
  display: grid;
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  place-items: center;
  color: #ffffff;
  background: var(--medicine-amber);
  border-radius: 8px;
  font-weight: 900;
}

.upload-card h3,
.section-title h3 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.section-help {
  display: block;
  max-width: 620px;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
  font-weight: 700;
}

input,
select,
textarea {
  width: 100%;
  color: var(--text-primary);
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
}

input {
  min-height: 42px;
  padding: 9px 12px;
}

select {
  min-height: 42px;
  padding: 9px 12px;
}

textarea {
  min-height: 180px;
  padding: 14px;
  resize: vertical;
  line-height: 1.75;
}

input:focus,
select:focus,
textarea:focus {
  background: #ffffff;
  border-color: var(--medical-blue);
}

.checkbox-label input {
  width: 16px;
  min-height: 16px;
  accent-color: var(--medical-blue);
}

.upload-card small {
  color: var(--pharmacy-teal);
  font-weight: 800;
}

.upload-result {
  display: grid;
  gap: 10px;
  padding: 12px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.upload-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-summary span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.upload-row {
  display: grid;
  gap: 7px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.upload-row strong {
  color: var(--text-primary);
  font-weight: 900;
}

.upload-row p {
  color: var(--text-secondary);
  line-height: 1.65;
}

.upload-status {
  width: max-content;
  padding: 3px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.upload-status.created {
  color: #166534;
  background: #f0fdf4;
}

.upload-status.updated {
  color: #92400e;
  background: #fffbeb;
}

.knowledge-panel,
.history-panel {
  min-height: 520px;
  padding: 22px;
}

.section-title {
  align-items: center;
  margin-bottom: 16px;
}

.tabs button {
  min-height: 36px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid var(--border);
}

.tabs button.active {
  color: #ffffff;
  background: var(--medical-blue);
}

.knowledge-list,
.review-list {
  display: grid;
  gap: 12px;
  max-height: 640px;
  overflow: auto;
  padding-right: 4px;
}

.knowledge-item,
.review-card,
.empty-state {
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.knowledge-item strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 900;
}

.knowledge-item span {
  display: inline-flex;
  margin-top: 6px;
  padding: 3px 8px;
  color: var(--medical-blue);
  background: #eff6ff;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.knowledge-item p,
.empty-state {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.review-card {
  background: #ffffff;
}

.review-header {
  align-items: flex-start;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.review-header strong {
  color: var(--text-primary);
  font-weight: 900;
}

.review-header span {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

pre {
  max-height: 160px;
  margin-top: 12px;
  overflow: auto;
  color: var(--text-secondary);
  white-space: pre-wrap;
  font-family: "Microsoft YaHei", Arial, sans-serif;
  line-height: 1.75;
}

.review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.review-meta span {
  padding: 4px 8px;
  color: var(--text-secondary);
  background: #f1f5f9;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 900;
}

.review-meta .danger-tag,
.review-meta .error-tag {
  color: #991b1b;
  background: #fef2f2;
}

.feedback-note {
  margin-top: 10px;
  padding: 10px 12px;
  color: var(--text-secondary);
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
  line-height: 1.7;
}

.mark-row {
  margin-top: 12px;
}

.mark-row input {
  flex: 1 1 260px;
}

.mark-row button {
  background: var(--danger);
}

@media (max-width: 980px) {
  .admin-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .user-create,
  .user-row,
  .delete-search,
  .delete-card {
    grid-template-columns: 1fr;
  }

  .review-summary,
  .issue-list,
  .agent-log-grid {
    grid-template-columns: 1fr;
  }

  .checkbox-label.compact {
    justify-content: flex-start;
  }

  .upload-grid,
  .admin-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .section-title,
  .review-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
