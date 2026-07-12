<template>
  <div class="auth-page">
    <section v-if="currentUser || guestMode" class="session-strip">
      <div>
        <span>当前状态</span>
        <strong>{{ currentUser?.username || '游客模式' }}</strong>
        <small>{{ sessionLabel }}</small>
      </div>

      <div class="session-actions">
        <RouterLink to="/chat">进入 AI 助手</RouterLink>
        <RouterLink v-if="currentUser?.role === 'admin'" to="/admin">管理后台</RouterLink>
        <button type="button" @click="logout">
          <LogOut :size="17" aria-hidden="true" />
          {{ currentUser ? '退出' : '退出游客模式' }}
        </button>
      </div>
    </section>

    <section class="auth-shell">
      <aside class="auth-intro">
        <span class="eyebrow">SECURE ACCESS</span>
        <h1>{{ introTitle }}</h1>
        <p>
          {{ introText }}
        </p>

        <div class="trust-list" aria-label="登录能力说明">
          <div>
            <ShieldCheck :size="20" aria-hidden="true" />
            <span>用户与管理员权限分离</span>
          </div>
          <div>
            <MessageSquareText :size="20" aria-hidden="true" />
            <span>个人历史会话可继续追问</span>
          </div>
          <div>
            <DatabaseZap :size="20" aria-hidden="true" />
            <span>管理员可维护知识库与日志</span>
          </div>
        </div>
      </aside>

      <form class="auth-card" @submit.prevent="submitForm">
        <div class="card-head">
          <div>
            <span>{{ cardKicker }}</span>
            <h2>{{ cardTitle }}</h2>
          </div>
        </div>

        <label class="field">
          <span>用户名</span>
          <div class="input-wrap">
            <UserRound :size="19" aria-hidden="true" />
            <input
              v-model.trim="username"
              autocomplete="username"
              autocapitalize="none"
              spellcheck="false"
              placeholder="请输入用户名"
              required
            />
          </div>
        </label>

        <label class="field">
          <span>密码</span>
          <div class="input-wrap">
            <LockKeyhole :size="19" aria-hidden="true" />
            <input
              v-model="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              :type="showPassword ? 'text' : 'password'"
              placeholder="至少 6 位"
              required
            />
            <button
              type="button"
              class="ghost-icon"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              :title="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" :size="18" aria-hidden="true" />
              <Eye v-else :size="18" aria-hidden="true" />
            </button>
          </div>
        </label>

        <label v-if="mode === 'register'" class="field">
          <span>确认密码</span>
          <div class="input-wrap">
            <LockKeyhole :size="19" aria-hidden="true" />
            <input
              v-model="confirmPassword"
              autocomplete="new-password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="再次输入密码"
              required
            />
          </div>
        </label>

        <p class="helper-text">
          {{ helperText }}
        </p>

        <button class="submit-btn" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="18" aria-hidden="true" />
          <UserPlus v-else-if="isRegister" :size="18" aria-hidden="true" />
          <LogIn v-else :size="18" aria-hidden="true" />
          {{ loading ? '处理中...' : mode === 'login' ? '登录并继续' : '创建账号' }}
        </button>

        <p v-if="message" :class="['message', success ? 'success' : 'error']">
          {{ message }}
        </p>

        <div class="auth-links">
          <RouterLink :to="alternatePath">{{ alternateText }}</RouterLink>
        </div>

        <div class="guest-divider">
          <span>或者</span>
        </div>

        <button class="guest-btn" type="button" @click="enterGuestMode">
          <MessageSquareText :size="18" aria-hidden="true" />
          游客体验 AI 咨询
        </button>
      </form>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DatabaseZap,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  LogOut,
  MessageSquareText,
  ShieldCheck,
  UserPlus,
  UserRound,
} from '@lucide/vue'
import { apiUrl } from '../api'

const props = defineProps({
  initialMode: {
    type: String,
    default: 'login',
  },
})

const route = useRoute()
const router = useRouter()

const mode = ref('login')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const message = ref('')
const success = ref(false)
const loading = ref(false)
const currentUser = ref(null)
const guestMode = ref(false)

const isRegister = computed(() => mode.value === 'register')

const helperText = computed(() => {
  if (!isRegister.value) {
    return '登录后会在本机保存访问令牌，用于恢复历史会话和区分管理员权限。'
  }

  return '注册仅需用户名和密码；请使用至少 6 位密码，注册后再登录。'
})

const introTitle = computed(() => (isRegister.value ? '注册普通用户账号' : '登录 AI 医疗 Agent 助手'))
const introText = computed(() => (
  isRegister.value
    ? '创建账号后可保存个人对话、从历史记录继续咨询；也可以先用游客模式直接体验 AI 咨询。'
    : '登录后可保存个人对话、从历史记录继续咨询；管理员账号可进入后台管理知识库、查看 Agent 调度日志。'
))
const cardKicker = computed(() => (isRegister.value ? '创建普通用户账号' : '欢迎回来'))
const cardTitle = computed(() => (isRegister.value ? '注册账号' : '登录账号'))
const alternatePath = computed(() => (isRegister.value ? '/login' : '/register'))
const alternateText = computed(() => (isRegister.value ? '已有账号？去登录' : '还没有账号？去注册'))
const sessionLabel = computed(() => {
  if (currentUser.value?.role === 'admin') {
    return '管理员'
  }

  if (currentUser.value) {
    return '普通用户'
  }

  return '无需账号，可体验咨询功能'
})
const redirectPath = computed(() => {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''

  if (redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect
  }

  return ''
})

const loadCurrentUser = () => {
  const raw = localStorage.getItem('ragUser')
  currentUser.value = raw ? JSON.parse(raw) : null
  guestMode.value = !currentUser.value && localStorage.getItem('ragGuest') === 'true'
}

const syncRouteState = () => {
  mode.value = props.initialMode === 'register' ? 'register' : 'login'
  message.value = ''
  success.value = false
  password.value = ''
  confirmPassword.value = ''

  if (!isRegister.value && route.query.registered === '1') {
    message.value = '注册成功，请使用刚才的账号登录。'
    success.value = true
  }

  if (typeof route.query.username === 'string') {
    username.value = route.query.username
  }
}

const validateForm = () => {
  if (!username.value.trim() || !password.value.trim()) {
    return '请输入用户名和密码'
  }

  if (username.value.trim().length < 3) {
    return '用户名至少 3 位'
  }

  if (password.value.length < 6) {
    return '密码至少 6 位'
  }

  if (isRegister.value && password.value !== confirmPassword.value) {
    return '两次输入的密码不一致'
  }

  return ''
}

const submitForm = async () => {
  const validationMessage = validateForm()
  if (validationMessage) {
    message.value = validationMessage
    success.value = false
    return
  }

  loading.value = true
  message.value = ''

  try {
    const response = await fetch(apiUrl(`/api/auth/${mode.value}`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username.value,
        password: password.value,
      }),
    })

    const data = await response.json()
    success.value = Boolean(data.success)
    message.value = data.message || (data.success ? '操作成功' : '操作失败')

    if (data.success && mode.value === 'login') {
      localStorage.setItem('ragUser', JSON.stringify(data.user))
      localStorage.setItem('ragToken', data.token)
      localStorage.removeItem('ragGuest')
      window.dispatchEvent(new Event('rag-user-change'))
      currentUser.value = data.user
      guestMode.value = false

      router.push(redirectPath.value || (data.user.role === 'admin' ? '/admin' : '/chat'))
    }

    if (data.success && mode.value === 'register') {
      const nextUsername = username.value
      username.value = ''
      password.value = ''
      confirmPassword.value = ''
      await router.push({
        path: '/login',
        query: {
          registered: '1',
          username: nextUsername,
          ...(redirectPath.value ? { redirect: redirectPath.value } : {}),
        },
      })
    }
  } catch (error) {
    console.error(error)
    success.value = false
    message.value = '请求失败，请检查后端服务是否正常运行。'
  } finally {
    loading.value = false
  }
}

const enterGuestMode = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  localStorage.setItem('ragGuest', 'true')
  window.dispatchEvent(new Event('rag-user-change'))
  currentUser.value = null
  guestMode.value = true
  router.push('/chat')
}

const logout = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  localStorage.removeItem('ragGuest')
  window.dispatchEvent(new Event('rag-user-change'))
  loadCurrentUser()
  message.value = '已退出登录'
  success.value = true
}

onMounted(() => {
  loadCurrentUser()
})

watch(
  () => [props.initialMode, route.query.registered, route.query.username],
  syncRouteState,
  { immediate: true },
)
</script>

<style scoped>
.auth-page {
  display: grid;
  gap: 18px;
}

.session-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.session-strip span,
.session-strip small,
.card-head span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.session-strip strong {
  display: block;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 900;
}

.session-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.session-actions a,
.session-actions button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 0 13px;
  text-decoration: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 900;
}

.session-actions a {
  color: #ffffff;
  background: var(--medical-blue);
}

.session-actions button {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.auth-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 440px);
  gap: 28px;
  align-items: stretch;
  min-height: 620px;
}

.auth-intro,
.auth-card {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.auth-intro {
  display: grid;
  align-content: center;
  padding: clamp(26px, 5vw, 54px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(232, 248, 250, 0.86)),
    #ffffff;
}

.eyebrow {
  margin-bottom: 12px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.auth-intro h1 {
  max-width: 620px;
  color: var(--text-primary);
  font-size: clamp(34px, 5vw, 54px);
  font-weight: 900;
  line-height: 1.1;
}

.auth-intro p {
  max-width: 640px;
  margin-top: 18px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.9;
}

.trust-list {
  display: grid;
  gap: 12px;
  margin-top: 30px;
}

.trust-list div {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 12px;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(14, 116, 144, 0.16);
  border-radius: 8px;
  font-weight: 800;
}

.trust-list svg {
  color: var(--pharmacy-teal);
  flex: 0 0 auto;
}

.auth-card {
  display: grid;
  align-content: center;
  gap: 16px;
  padding: clamp(22px, 4vw, 32px);
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-head h2 {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 28px;
  font-weight: 900;
}

.field {
  display: grid;
  gap: 8px;
  color: var(--text-primary);
  font-weight: 900;
}

.input-wrap {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 12px;
  color: var(--text-muted);
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.input-wrap:focus-within {
  color: var(--medical-blue);
  background: #ffffff;
  border-color: var(--medical-blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-wrap input {
  width: 100%;
  min-height: 46px;
  padding: 0;
  color: var(--text-primary);
  background: transparent;
  border: 0;
  outline: none;
  font: inherit;
}

.ghost-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  color: var(--text-muted);
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.ghost-icon:hover {
  color: var(--medical-blue);
  background: #eff6ff;
}

.helper-text {
  margin: -2px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 18px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--pharmacy-teal));
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
  box-shadow: 0 14px 26px rgba(37, 99, 235, 0.22);
}

.submit-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.message {
  margin: 0;
  padding: 11px 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 800;
}

.message.success {
  color: #166534;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.message.error {
  color: #991b1b;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.auth-links {
  display: flex;
  justify-content: center;
  margin-top: -2px;
}

.auth-links a {
  color: var(--medical-blue);
  text-decoration: none;
  font-weight: 900;
}

.auth-links a:hover {
  color: var(--medical-blue-dark);
}

.guest-divider {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 900;
}

.guest-divider::before,
.guest-divider::after {
  height: 1px;
  content: "";
  background: var(--border);
}

.guest-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 46px;
  padding: 0 18px;
  color: var(--pharmacy-teal);
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
}

.guest-btn:hover {
  color: #0f766e;
  background: #d1fae5;
}

@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
    min-height: 0;
  }

  .auth-intro {
    align-content: start;
  }
}

@media (max-width: 640px) {
  .session-strip,
  .card-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .session-actions {
    width: 100%;
  }

  .session-actions a,
  .session-actions button {
    flex: 1 1 140px;
    justify-content: center;
  }
}
</style>
