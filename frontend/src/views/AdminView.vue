<template>
  <div v-if="!isAdmin" class="access-gate">
    <p class="eyebrow">ADMIN ONLY</p>
    <h2>需要管理员登录</h2>
    <p>管理员后台包含知识库写入、向量索引更新和问答审核操作，请先使用管理员账号登录。</p>
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
        <button type="button" @click="loadAdminData" :disabled="loading">
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

    <section class="upload-grid" aria-label="知识文档上传">
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
      </article>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { apiUrl } from '../api'

const user = ref(null)
const loading = ref(false)
const indexLoading = ref(false)
const statusMessage = ref('')
const historyList = ref([])
const users = ref([])
const userSaving = ref(false)
const activeKnowledge = ref('disease')
const errorReasons = reactive({})
const userEdits = reactive({})

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
  },
  medicine: {
    fileName: '',
    content: '',
    loading: false,
    message: '',
  },
})

const isAdmin = computed(() => user.value?.role === 'admin')

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return {
    ...extra,
    Authorization: `Bearer ${token}`,
  }
}

const parseAdminResponse = async (response) => {
  if (response.status === 401 || response.status === 403) {
    statusMessage.value = '管理员登录已失效或权限不足，请重新登录管理员账号。'
    throw new Error('admin forbidden')
  }

  return response.json()
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

const loadAdminData = async () => {
  if (!isAdmin.value) {
    return
  }

  loading.value = true
  statusMessage.value = ''

  try {
    const [knowledgeResponse, historyResponse, usersResponse] = await Promise.all([
      fetch(apiUrl('/api/admin/knowledge'), {
        headers: authHeaders(),
      }),
      fetch(apiUrl('/api/admin/history'), {
        headers: authHeaders(),
      }),
      fetch(apiUrl('/api/admin/users'), {
        headers: authHeaders(),
      }),
    ])

    knowledge.value = await parseAdminResponse(knowledgeResponse)
    const historyData = await parseAdminResponse(historyResponse)
    const usersData = await parseAdminResponse(usersResponse)
    historyList.value = historyData.data || []
    users.value = usersData.data || []
    syncUserEdits()
  } catch (error) {
    console.error(error)
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
      await loadAdminData()
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
    await loadAdminData()
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
    await loadAdminData()
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

  const reader = new FileReader()
  reader.onload = () => {
    uploads[kind].content = String(reader.result || '')
  }
  reader.readAsText(file, 'utf-8')
}

const uploadDoc = async (kind) => {
  const target = uploads[kind]

  if (!target.content.trim()) {
    target.message = '请先选择文件或粘贴文档内容。'
    return
  }

  target.loading = true
  target.message = ''

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

    if (data.success) {
      target.content = ''
      target.fileName = ''
      await loadAdminData()
    }
  } catch (error) {
    console.error(error)
    target.message = '上传失败，请检查后端服务是否正常运行。'
  } finally {
    target.loading = false
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
    statusMessage.value = `${data.message}，文档数：${data.data.doc_count}，向量维度：${data.data.dimension}`
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
    await loadAdminData()
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
.user-panel,
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

.upload-grid,
.admin-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
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
  .user-row {
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
