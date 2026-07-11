<template>
  <div class="profile-page">
    <section v-if="!currentUser" class="profile-empty">
      <div>
        <span>尚未登录</span>
        <h1>登录后查看个人中心</h1>
        <p>登录后可以查看账号身份、继续历史会话，并进入 AI 助手保存新的咨询记录。</p>
      </div>

      <RouterLink class="primary-link" to="/login">去登录/注册</RouterLink>
    </section>

    <template v-else>
      <section class="profile-hero">
        <div class="avatar" aria-hidden="true">{{ userInitial }}</div>
        <div>
          <span class="eyebrow">个人中心</span>
          <h1>{{ currentUser.username }}</h1>
          <p>{{ roleLabel }} · 登录后会自动保存 AI 助手对话和历史咨询记录。</p>
        </div>

        <button type="button" class="logout-btn" @click="logout">
          <LogOut :size="18" aria-hidden="true" />
          退出登录
        </button>
      </section>

      <section class="profile-grid">
        <div class="profile-card account-card">
          <div class="card-title">
            <UserRound :size="20" aria-hidden="true" />
            <strong>账号信息</strong>
          </div>

          <dl>
            <div>
              <dt>用户名</dt>
              <dd>{{ currentUser.username }}</dd>
            </div>
            <div>
              <dt>身份</dt>
              <dd>{{ roleLabel }}</dd>
            </div>
            <div>
              <dt>历史会话</dt>
              <dd>{{ conversationSessions.length }} 个</dd>
            </div>
            <div>
              <dt>消息记录</dt>
              <dd>{{ totalMessages }} 条</dd>
            </div>
          </dl>
        </div>

        <div class="profile-card action-card">
          <div class="card-title">
            <Sparkles :size="20" aria-hidden="true" />
            <strong>常用入口</strong>
          </div>

          <div class="quick-actions">
            <RouterLink to="/chat">
              <MessageSquareText :size="19" aria-hidden="true" />
              AI 助手
            </RouterLink>
            <RouterLink to="/history">
              <History :size="19" aria-hidden="true" />
              历史记录
            </RouterLink>
            <RouterLink to="/knowledge">
              <BookOpenText :size="19" aria-hidden="true" />
              知识库
            </RouterLink>
            <RouterLink v-if="currentUser.role === 'admin'" to="/admin">
              <ShieldCheck :size="19" aria-hidden="true" />
              管理后台
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="profile-card sessions-card">
        <div class="section-head">
          <div class="card-title">
            <History :size="20" aria-hidden="true" />
            <strong>最近会话</strong>
          </div>

          <button type="button" :disabled="sessionsLoading" @click="loadConversationSessions(true)">
            <RefreshCw :size="16" aria-hidden="true" />
            {{ sessionsLoading ? '刷新中' : '刷新' }}
          </button>
        </div>

        <p v-if="sessionsStatus" class="status-text">{{ sessionsStatus }}</p>

        <div v-if="sessionsLoading" class="empty-line">正在加载最近会话...</div>
        <div v-else-if="conversationSessions.length === 0" class="empty-line">
          暂无历史会话。去 AI 助手发送第一条消息后，这里会自动显示。
        </div>
        <div v-else class="session-list">
          <RouterLink
            v-for="session in recentSessions"
            :key="session.id"
            :to="{ path: '/chat', query: { session_id: session.id } }"
          >
            <span>{{ session.title || `会话 #${session.id}` }}</span>
            <small>{{ session.message_count || 0 }} 条消息</small>
          </RouterLink>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BookOpenText,
  History,
  LogOut,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-vue-next'
import { cachedGetJson, clearPageCacheByPrefix } from '../api'

const router = useRouter()

const currentUser = ref(null)
const conversationSessions = ref([])
const sessionsLoading = ref(false)
const sessionsStatus = ref('')

const userInitial = computed(() => currentUser.value?.username?.slice(0, 1)?.toUpperCase() || '用')
const roleLabel = computed(() => currentUser.value?.role === 'admin' ? '管理员' : '普通用户')
const recentSessions = computed(() => conversationSessions.value.slice(0, 5))
const totalMessages = computed(() => conversationSessions.value.reduce(
  (sum, session) => sum + Number(session.message_count || 0),
  0,
))

const authHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('ragToken') || ''}`,
})

const profileSessionsCacheKey = () => {
  const userKey = currentUser.value?.id || currentUser.value?.username || 'guest'
  return `profile:sessions:${userKey}`
}

const loadCurrentUser = () => {
  const raw = localStorage.getItem('ragUser')
  currentUser.value = raw ? JSON.parse(raw) : null
}

const loadConversationSessions = async (force = false) => {
  if (!currentUser.value) return

  sessionsLoading.value = true
  sessionsStatus.value = ''

  try {
    const data = await cachedGetJson(
      profileSessionsCacheKey(),
      '/api/conversations/sessions',
      {
        force,
        fetchOptions: {
          headers: authHeaders(),
        },
      },
    )

    if (!Array.isArray(data.data)) {
      conversationSessions.value = []
      sessionsStatus.value = data.message || '最近会话加载失败。'
      return
    }

    conversationSessions.value = data.data || []
    sessionsStatus.value = data.message || ''
  } catch (error) {
    console.error(error)
    conversationSessions.value = []
    sessionsStatus.value = '最近会话加载失败，请检查后端服务。'
  } finally {
    sessionsLoading.value = false
  }
}

const logout = () => {
  clearPageCacheByPrefix('profile:')
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  window.dispatchEvent(new Event('rag-user-change'))
  currentUser.value = null
  router.push('/login')
}

onMounted(() => {
  loadCurrentUser()
  loadConversationSessions()
})
</script>

<style scoped>
.profile-page {
  display: grid;
  gap: 18px;
}

.profile-empty,
.profile-hero,
.profile-card {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.profile-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: clamp(22px, 4vw, 34px);
}

.profile-empty span,
.eyebrow,
dt,
.status-text,
.empty-line {
  color: var(--text-muted);
}

.profile-empty h1,
.profile-hero h1 {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 900;
  line-height: 1.2;
}

.profile-empty p,
.profile-hero p {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.primary-link,
.logout-btn,
.section-head button,
.quick-actions a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
  text-decoration: none;
}

.primary-link,
.quick-actions a:first-child {
  color: #ffffff;
  background: var(--medical-blue);
}

.profile-hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  padding: clamp(20px, 4vw, 32px);
}

.avatar {
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 8px;
  font-size: 30px;
  font-weight: 900;
}

.eyebrow {
  font-size: 12px;
  font-weight: 900;
}

.logout-btn {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 0.8fr);
  gap: 18px;
}

.profile-card {
  padding: 18px;
}

.card-title,
.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-head {
  justify-content: space-between;
  margin-bottom: 14px;
}

.card-title {
  color: var(--text-primary);
}

.card-title svg {
  color: var(--medical-blue);
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

dl div {
  padding: 12px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
}

dt {
  font-size: 12px;
  font-weight: 900;
}

dd {
  margin: 4px 0 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.quick-actions a {
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
}

.quick-actions a:hover {
  color: var(--medical-blue);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.quick-actions a:first-child:hover {
  color: #ffffff;
  background: var(--medical-blue-dark);
  border-color: var(--medical-blue-dark);
}

.section-head button {
  color: var(--text-secondary);
  background: #f8fafc;
  border: 1px solid var(--border);
}

.section-head button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-text,
.empty-line {
  margin: 0;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
  line-height: 1.7;
}

.session-list {
  display: grid;
  gap: 10px;
}

.session-list a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 50px;
  padding: 10px 12px;
  color: var(--text-primary);
  text-decoration: none;
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.session-list a:hover {
  color: var(--medical-blue);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.session-list span,
.session-list small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-list span {
  font-weight: 900;
}

.session-list small {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 820px) {
  .profile-hero,
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .profile-empty,
  .profile-hero {
    align-items: flex-start;
  }

  .logout-btn {
    width: fit-content;
  }
}

@media (max-width: 560px) {
  .profile-empty,
  .section-head,
  .session-list a {
    align-items: flex-start;
    flex-direction: column;
  }

  dl,
  .quick-actions {
    grid-template-columns: 1fr;
  }

  .primary-link,
  .logout-btn,
  .section-head button {
    width: 100%;
  }
}
</style>
