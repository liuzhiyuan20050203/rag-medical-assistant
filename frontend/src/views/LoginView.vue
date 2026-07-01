<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="auth-copy">
        <p class="eyebrow">ACCOUNT ACCESS</p>
        <h2>登录 / 注册</h2>
        <p>
          登录后可以进入管理后台。普通用户可注册账号，管理员演示账号由后端自动初始化。
        </p>

        <div class="demo-account">
          <span>管理员演示账号</span>
          <strong>admin / admin123</strong>
        </div>
      </div>

      <form class="auth-form" @submit.prevent="submitForm">
        <div class="mode-switch" aria-label="账号模式">
          <button
            type="button"
            :class="{ active: mode === 'login' }"
            @click="mode = 'login'"
          >
            登录
          </button>
          <button
            type="button"
            :class="{ active: mode === 'register' }"
            @click="mode = 'register'"
          >
            注册
          </button>
        </div>

        <label>
          用户名
          <input
            v-model="username"
            autocomplete="username"
            placeholder="请输入用户名"
          />
        </label>

        <label>
          密码
          <input
            v-model="password"
            autocomplete="current-password"
            type="password"
            placeholder="至少 6 位"
          />
        </label>

        <button class="submit-btn" type="submit" :disabled="loading">
          {{ loading ? '处理中...' : mode === 'login' ? '登录系统' : '创建账号' }}
        </button>

        <p v-if="message" :class="['message', success ? 'success' : 'error']">
          {{ message }}
        </p>
      </form>
    </section>

    <section v-if="currentUser" class="current-user">
      <div>
        <span>当前登录</span>
        <strong>{{ currentUser.username }}</strong>
        <small>{{ currentUser.role === 'admin' ? '管理员' : '普通用户' }}</small>
      </div>

      <div class="user-actions">
        <RouterLink v-if="currentUser.role === 'admin'" to="/admin">进入管理后台</RouterLink>
        <RouterLink to="/">返回首页</RouterLink>
        <button type="button" @click="logout">退出登录</button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const mode = ref('login')
const username = ref('admin')
const password = ref('admin123')
const message = ref('')
const success = ref(false)
const loading = ref(false)
const currentUser = ref(null)

const loadCurrentUser = () => {
  const raw = localStorage.getItem('ragUser')
  currentUser.value = raw ? JSON.parse(raw) : null
}

const submitForm = async () => {
  if (!username.value.trim() || !password.value.trim()) {
    message.value = '请输入用户名和密码'
    success.value = false
    return
  }

  loading.value = true
  message.value = ''

  try {
    const response = await fetch(`http://127.0.0.1:8000/api/auth/${mode.value}`, {
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
    message.value = data.message

    if (data.success && mode.value === 'login') {
      localStorage.setItem('ragUser', JSON.stringify(data.user))
      localStorage.setItem('ragToken', data.token)
      window.dispatchEvent(new Event('rag-user-change'))
      currentUser.value = data.user

      if (data.user.role === 'admin') {
        router.push('/admin')
      }
    }

    if (data.success && mode.value === 'register') {
      mode.value = 'login'
      message.value = '注册成功，请登录。'
    }
  } catch (error) {
    console.error(error)
    success.value = false
    message.value = '请求失败，请检查后端服务是否正常运行。'
  } finally {
    loading.value = false
  }
}

const logout = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  window.dispatchEvent(new Event('rag-user-change'))
  loadCurrentUser()
  message.value = '已退出登录'
  success.value = true
}

onMounted(() => {
  loadCurrentUser()
})
</script>

<style scoped>
.auth-page {
  display: grid;
  gap: 22px;
}

.auth-panel {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(340px, 0.75fr);
  gap: 32px;
  align-items: stretch;
  padding: clamp(24px, 4vw, 42px);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(236, 253, 245, 0.82)),
    #ffffff;
  border: 1px solid rgba(14, 116, 144, 0.16);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.eyebrow {
  margin-bottom: 10px;
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.auth-copy h2 {
  color: var(--text-primary);
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 900;
  line-height: 1.15;
}

.auth-copy p {
  max-width: 620px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.9;
}

.demo-account {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 24px;
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.demo-account span,
.current-user span,
.current-user small {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.demo-account strong {
  color: var(--medical-blue);
  font-size: 18px;
  font-weight: 900;
}

.auth-form {
  display: grid;
  gap: 16px;
  padding: 22px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
}

.mode-switch {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  padding: 5px;
  background: #f1f8fb;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.mode-switch button,
.submit-btn,
.current-user button,
.current-user a {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
  text-decoration: none;
}

.mode-switch button {
  color: var(--text-secondary);
  background: transparent;
}

.mode-switch button.active {
  color: #ffffff;
  background: var(--medical-blue);
}

label {
  display: grid;
  gap: 8px;
  color: var(--text-primary);
  font-weight: 900;
}

input {
  width: 100%;
  min-height: 46px;
  padding: 0 14px;
  color: var(--text-primary);
  background: #f8fbfd;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
}

input:focus {
  border-color: var(--medical-blue);
  background: #ffffff;
}

.submit-btn {
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--pharmacy-teal));
}

.submit-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.message {
  padding: 12px 14px;
  border-radius: 8px;
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

.current-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.current-user strong {
  display: block;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.current-user small {
  display: block;
}

.user-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.current-user a {
  display: inline-flex;
  align-items: center;
  color: #ffffff;
  background: var(--medical-blue);
}

.current-user button {
  color: var(--danger);
  background: #fef2f2;
  border: 1px solid #fecaca;
}

@media (max-width: 820px) {
  .auth-panel {
    grid-template-columns: 1fr;
  }

  .current-user {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
