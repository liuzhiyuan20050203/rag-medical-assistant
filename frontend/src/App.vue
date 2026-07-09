<template>
  <div class="app">
    <header class="header">
      <RouterLink class="brand" to="/" aria-label="返回首页">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" role="img">
            <path d="M9.2 3.8h5.6v5.4h5.4v5.6h-5.4v5.4H9.2v-5.4H3.8V9.2h5.4z" />
          </svg>
        </span>

        <span>
          <strong>AI 医疗 Agent 助手</strong>
          <small>症状咨询 · 用药核对 · 图片语音输入</small>
        </span>
      </RouterLink>

      <div class="header-actions">
        <nav class="nav" aria-label="主导航">
          <RouterLink to="/">首页</RouterLink>
          <RouterLink to="/chat">AI 助手</RouterLink>
          <RouterLink to="/knowledge">知识库</RouterLink>
          <RouterLink to="/history">历史记录</RouterLink>
          <RouterLink v-if="isAdmin" to="/analytics">数据分析</RouterLink>
          <RouterLink v-if="isAdmin" to="/admin">管理后台</RouterLink>
        </nav>

        <div ref="accountMenuRef" class="account-menu">
          <button
            type="button"
            class="avatar-button"
            :class="{ active: accountMenuOpen }"
            :aria-expanded="accountMenuOpen"
            aria-label="打开用户菜单"
            @click="toggleAccountMenu"
          >
            <span class="avatar-shell">
              <img v-if="currentUser?.avatar" :src="currentUser.avatar" alt="用户头像" />
              <span v-else>{{ avatarText }}</span>
            </span>
            <span class="account-name">{{ accountLabel }}</span>
            <ChevronDown :class="{ open: accountMenuOpen }" :size="15" aria-hidden="true" />
          </button>

          <div v-if="accountMenuOpen" class="account-dropdown">
            <div class="account-summary">
              <span class="avatar-shell large">
                <img v-if="currentUser?.avatar" :src="currentUser.avatar" alt="用户头像" />
                <span v-else>{{ avatarText }}</span>
              </span>
              <div>
                <strong>{{ accountLabel }}</strong>
                <small>{{ accountSubtext }}</small>
              </div>
            </div>

            <RouterLink v-if="currentUser" to="/profile" @click="closeAccountMenu">
              <Settings :size="17" aria-hidden="true" />
              个人设置
            </RouterLink>
            <RouterLink v-if="!currentUser" to="/login" @click="closeAccountMenu">
              <LogIn :size="17" aria-hidden="true" />
              登录
            </RouterLink>
            <RouterLink v-if="!currentUser" to="/register" @click="closeAccountMenu">
              <UserPlus :size="17" aria-hidden="true" />
              注册
            </RouterLink>
            <button v-if="!currentUser && !guestMode" type="button" @click="enterGuestMode">
              <UserRound :size="17" aria-hidden="true" />
              游客体验
            </button>
            <button v-if="currentUser || guestMode" type="button" class="danger-action" @click="logout">
              <LogOut :size="17" aria-hidden="true" />
              {{ currentUser ? '退出登录' : '退出游客模式' }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChevronDown,
  LogIn,
  LogOut,
  Settings,
  UserPlus,
  UserRound,
} from '@lucide/vue'

const router = useRouter()
const currentUser = ref(null)
const guestMode = ref(false)
const accountMenuOpen = ref(false)
const accountMenuRef = ref(null)

const loadCurrentUser = () => {
  try {
    const raw = localStorage.getItem('ragUser')
    currentUser.value = raw ? JSON.parse(raw) : null
  } catch (error) {
    console.error(error)
    currentUser.value = null
  }

  guestMode.value = !currentUser.value && localStorage.getItem('ragGuest') === 'true'
}

const isAdmin = computed(() => currentUser.value?.role === 'admin')
const accountDisplayName = computed(() => currentUser.value?.display_name || currentUser.value?.username || '')
const accountLabel = computed(() => {
  if (accountDisplayName.value) {
    return accountDisplayName.value
  }

  return guestMode.value ? '游客模式' : '未登录'
})
const accountSubtext = computed(() => {
  if (currentUser.value?.role === 'admin') {
    return '管理员账号'
  }

  if (currentUser.value) {
    return currentUser.value.username
  }

  return guestMode.value ? '可直接体验咨询功能' : '登录后保存个人资料'
})
const avatarText = computed(() => {
  if (guestMode.value) {
    return '游'
  }

  const text = accountDisplayName.value || '访客'
  return text.slice(0, 2).toUpperCase()
})

const closeAccountMenu = () => {
  accountMenuOpen.value = false
}

const toggleAccountMenu = () => {
  accountMenuOpen.value = !accountMenuOpen.value
}

const handleDocumentClick = (event) => {
  if (!accountMenuRef.value?.contains(event.target)) {
    closeAccountMenu()
  }
}

const enterGuestMode = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  localStorage.setItem('ragGuest', 'true')
  window.dispatchEvent(new Event('rag-user-change'))
  loadCurrentUser()
  closeAccountMenu()
  router.push('/chat')
}

const logout = () => {
  localStorage.removeItem('ragUser')
  localStorage.removeItem('ragToken')
  localStorage.removeItem('ragGuest')
  window.dispatchEvent(new Event('rag-user-change'))
  loadCurrentUser()
  closeAccountMenu()
  router.push('/login')
}

onMounted(() => {
  loadCurrentUser()
  window.addEventListener('storage', loadCurrentUser)
  window.addEventListener('rag-user-change', loadCurrentUser)
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', loadCurrentUser)
  window.removeEventListener('rag-user-change', loadCurrentUser)
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  color: var(--text-primary);
  background:
    linear-gradient(180deg, rgba(230, 248, 255, 0.78), rgba(247, 250, 252, 0.62) 320px),
    var(--page-bg);
}

.header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  min-height: 72px;
  padding: 12px clamp(18px, 4vw, 56px);
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid rgba(29, 78, 216, 0.1);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(18px);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 230px;
  color: var(--text-primary);
  text-decoration: none;
}

.brand:hover {
  color: var(--text-primary);
}

.brand-mark {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 8px;
  box-shadow: 0 12px 22px rgba(14, 116, 144, 0.25);
}

.brand-mark svg {
  width: 25px;
  height: 25px;
  fill: currentColor;
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 17px;
  font-weight: 800;
  line-height: 1.25;
}

.brand small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  min-width: 0;
}

.nav {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.nav a {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 13px;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  transition:
    color 0.2s ease,
    background-color 0.2s ease,
    box-shadow 0.2s ease;
}

.nav a:hover {
  color: var(--medical-blue);
  background: #eff6ff;
}

.nav a.router-link-active {
  color: #ffffff;
  background: var(--medical-blue);
  box-shadow: 0 10px 18px rgba(37, 99, 235, 0.22);
}

.account-menu {
  position: relative;
  flex: 0 0 auto;
}

.avatar-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 4px 9px 4px 5px;
  color: var(--text-secondary);
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 999px;
  cursor: pointer;
  font-weight: 800;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.avatar-button:hover,
.avatar-button.active {
  color: var(--medical-blue);
  background: #eff6ff;
  border-color: var(--info-border);
}

.avatar-button svg {
  transition: transform 0.2s ease;
}

.avatar-button svg.open {
  transform: rotate(180deg);
}

.avatar-shell {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  overflow: hidden;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 999px;
  font-size: 13px;
  font-weight: 900;
}

.avatar-shell.large {
  width: 46px;
  height: 46px;
  font-size: 16px;
}

.avatar-shell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account-name {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 30;
  display: grid;
  gap: 7px;
  width: min(300px, calc(100vw - 32px));
  padding: 12px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
}

.account-summary {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.account-summary strong,
.account-summary small {
  display: block;
}

.account-summary strong {
  color: var(--text-primary);
  font-weight: 900;
}

.account-summary small {
  max-width: 190px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown a,
.account-dropdown button {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  padding: 0 10px;
  color: var(--text-secondary);
  text-align: left;
  text-decoration: none;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 900;
}

.account-dropdown a:hover,
.account-dropdown button:hover {
  color: var(--medical-blue);
  background: #eff6ff;
}

.account-dropdown .danger-action {
  color: #991b1b;
}

.account-dropdown .danger-action:hover {
  color: #991b1b;
  background: #fef2f2;
}

.main {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 34px 0 56px;
}

@media (max-width: 980px) {
  .header {
    position: static;
    align-items: flex-start;
    flex-direction: column;
  }

  .brand {
    min-width: 0;
  }

  .header-actions {
    align-items: stretch;
    flex-direction: column;
    width: 100%;
  }

  .nav {
    justify-content: flex-start;
    width: 100%;
  }

  .nav a {
    flex: 1 1 120px;
    justify-content: center;
  }

  .account-menu {
    align-self: flex-start;
  }
}
</style>
