<template>
  <div class="app">
    <aside class="sidebar" aria-label="主导航">
      <RouterLink class="brand" to="/" aria-label="返回首页">
        <span class="brand-mark" aria-hidden="true">
          <HeartPulse :size="25" :stroke-width="2.4" />
        </span>
        <span class="brand-copy">
          <strong>MedAgent AI</strong>
          <small>健康咨询助手</small>
        </span>
      </RouterLink>

      <nav class="sidebar-nav">
        <RouterLink to="/">
          <LayoutDashboard :size="23" aria-hidden="true" />
          <span>首页</span>
        </RouterLink>
        <RouterLink to="/analytics">
          <ChartNoAxesCombined :size="23" aria-hidden="true" />
          <span>数据分析</span>
        </RouterLink>
        <RouterLink to="/chat">
          <MessageSquareText :size="23" aria-hidden="true" />
          <span>AI 咨询</span>
        </RouterLink>
        <RouterLink to="/knowledge">
          <BookOpen :size="23" aria-hidden="true" />
          <span>知识库</span>
        </RouterLink>
        <RouterLink to="/history">
          <History :size="23" aria-hidden="true" />
          <span>咨询记录</span>
        </RouterLink>
      </nav>

      <nav class="sidebar-footer" aria-label="辅助导航">
        <RouterLink to="/profile">
          <Settings :size="22" aria-hidden="true" />
          <span>设置</span>
        </RouterLink>
        <RouterLink to="/about">
          <CircleHelp :size="22" aria-hidden="true" />
          <span>支持</span>
        </RouterLink>
      </nav>
    </aside>

    <header class="topbar">
      <RouterLink class="mobile-brand" to="/" aria-label="返回首页">
        <span class="brand-mark compact" aria-hidden="true">
          <HeartPulse :size="21" :stroke-width="2.4" />
        </span>
        <strong>MedAgent AI</strong>
      </RouterLink>

      <div class="page-identity">
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageSubtitle }}</p>
      </div>

      <nav class="mobile-nav" aria-label="移动端主导航">
        <RouterLink to="/" aria-label="首页">
          <LayoutDashboard :size="20" aria-hidden="true" />
          <span>首页</span>
        </RouterLink>
        <RouterLink to="/analytics" aria-label="数据分析">
          <ChartNoAxesCombined :size="20" aria-hidden="true" />
          <span>分析</span>
        </RouterLink>
        <RouterLink to="/chat" aria-label="AI 咨询">
          <MessageSquareText :size="20" aria-hidden="true" />
          <span>咨询</span>
        </RouterLink>
        <RouterLink to="/knowledge" aria-label="知识库">
          <BookOpen :size="20" aria-hidden="true" />
          <span>知识库</span>
        </RouterLink>
        <RouterLink to="/history" aria-label="咨询记录">
          <History :size="20" aria-hidden="true" />
          <span>记录</span>
        </RouterLink>
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
          <ChevronDown :class="{ open: accountMenuOpen }" :size="16" aria-hidden="true" />
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
            <Settings :size="18" aria-hidden="true" />
            个人设置
          </RouterLink>
          <RouterLink v-if="isAdmin" to="/analytics" @click="closeAccountMenu">
            <ChartNoAxesCombined :size="18" aria-hidden="true" />
            数据分析
          </RouterLink>
          <RouterLink v-if="isAdmin" to="/admin" @click="closeAccountMenu">
            <ShieldAlert :size="18" aria-hidden="true" />
            管理后台
          </RouterLink>
          <RouterLink v-if="!currentUser" to="/login" @click="closeAccountMenu">
            <LogIn :size="18" aria-hidden="true" />
            登录
          </RouterLink>
          <RouterLink v-if="!currentUser" to="/register" @click="closeAccountMenu">
            <UserPlus :size="18" aria-hidden="true" />
            注册
          </RouterLink>
          <button v-if="!currentUser && !guestMode" type="button" @click="enterGuestMode">
            <UserRound :size="18" aria-hidden="true" />
            游客体验
          </button>
          <button v-if="currentUser || guestMode" type="button" class="danger-action" @click="logout">
            <LogOut :size="18" aria-hidden="true" />
            {{ currentUser ? '退出登录' : '退出游客模式' }}
          </button>
        </div>
      </div>
    </header>

    <main class="main">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BookOpen,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  HeartPulse,
  History,
  LayoutDashboard,
  LogIn,
  LogOut,
  MessageSquareText,
  Settings,
  ShieldAlert,
  UserPlus,
  UserRound,
} from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const currentUser = ref(null)
const guestMode = ref(false)
const accountMenuOpen = ref(false)
const accountMenuRef = ref(null)

const pageCopy = {
  home: ['工作台概览', '欢迎使用 MedAgent 医疗助手'],
  chat: ['AI 智能咨询', '更清晰、更易操作的健康咨询空间'],
  knowledge: ['知识库检索', '查询常见病、药品与危险警示规则'],
  analytics: ['数据分析', '查看系统使用与安全分诊概况'],
  history: ['咨询记录', '查找并继续以往的健康咨询'],
  medicine: ['药品信息', '核对药品用途、禁忌与注意事项'],
  multimodal: ['图片与语音', '补充药盒、报告和症状图片线索'],
  profile: ['个人设置', '管理账号与个性化选项'],
  login: ['账号登录', '登录后可保存并继续咨询'],
  register: ['注册账号', '创建账号以保存咨询记录'],
  admin: ['管理后台', '系统数据和服务配置'],
  about: ['帮助与支持', '了解系统能力与安全边界'],
}

const currentPageCopy = computed(() => pageCopy[route.name] || ['MedAgent 医疗助手', '智能健康信息服务'])
const pageTitle = computed(() => currentPageCopy.value[0])
const pageSubtitle = computed(() => currentPageCopy.value[1])

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
  if (accountDisplayName.value) return accountDisplayName.value
  return guestMode.value ? '游客模式' : '未登录'
})
const accountSubtext = computed(() => {
  if (currentUser.value?.role === 'admin') return '管理员账号'
  if (currentUser.value) return currentUser.value.username
  return guestMode.value ? '可直接体验咨询功能' : '登录后保存个人资料'
})
const avatarText = computed(() => {
  if (guestMode.value) return '游'
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
  if (!accountMenuRef.value?.contains(event.target)) closeAccountMenu()
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
  background: var(--page-bg);
}

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 30;
  display: flex;
  width: var(--sidebar-width);
  flex-direction: column;
  padding: 24px 0;
  background: var(--surface);
  border-right: 1px solid var(--outline-variant);
}

.brand,
.mobile-brand {
  color: var(--text-primary);
  text-decoration: none;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 0 24px;
}

.brand-mark {
  display: grid;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  place-items: center;
  color: #fff;
  background: var(--primary);
  border-radius: var(--radius-md);
}

.brand-mark.compact {
  width: 38px;
  height: 38px;
}

.brand-copy strong,
.brand-copy small {
  display: block;
}

.brand-copy strong {
  color: var(--primary);
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.brand-copy small {
  margin-top: 1px;
  color: var(--text-secondary);
  font-size: 13px;
}

.sidebar-nav,
.sidebar-footer {
  display: grid;
  gap: 4px;
}

.sidebar-nav {
  flex: 1 1 auto;
  align-content: start;
  margin-top: 34px;
}

.sidebar-footer {
  padding-top: 18px;
  border-top: 1px solid var(--outline-variant);
}

.sidebar-nav a,
.sidebar-footer a {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 56px;
  padding: 0 24px 0 28px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 17px;
  font-weight: 650;
  transition: color 0.18s ease, background-color 0.18s ease;
}

.sidebar-nav a:hover,
.sidebar-footer a:hover {
  color: var(--primary);
  background: var(--surface-container-high);
}

.sidebar-nav a.router-link-active {
  color: var(--primary);
  background: var(--primary-soft);
}

.sidebar-nav a.router-link-active::before {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  content: '';
  background: var(--primary);
}

.topbar {
  position: fixed;
  inset: 0 0 auto var(--sidebar-width);
  z-index: 25;
  display: flex;
  height: var(--topbar-height);
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 clamp(18px, 3vw, 32px);
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--outline-variant);
  backdrop-filter: blur(16px);
}

.mobile-brand,
.mobile-nav {
  display: none;
}

.page-identity h1 {
  font-size: 21px;
  font-weight: 800;
  line-height: 1.25;
}

.page-identity p {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.35;
}

.account-menu {
  position: relative;
  flex: 0 0 auto;
}

.avatar-button {
  display: inline-flex;
  min-height: 46px;
  align-items: center;
  gap: 9px;
  padding: 4px 11px 4px 5px;
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-pill);
  cursor: pointer;
  font-weight: 750;
}

.avatar-button:hover,
.avatar-button.active {
  color: var(--primary);
  border-color: var(--primary);
}

.avatar-button svg {
  transition: transform 0.2s ease;
}

.avatar-button svg.open {
  transform: rotate(180deg);
}

.avatar-shell {
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, var(--primary), var(--teal-bright));
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 900;
}

.avatar-shell.large {
  width: 48px;
  height: 48px;
  font-size: 16px;
}

.avatar-shell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 40;
  display: grid;
  gap: 6px;
  width: min(304px, calc(100vw - 28px));
  padding: 12px;
  background: #fff;
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.account-summary {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 2px;
  padding: 10px;
  background: var(--surface-container-low);
  border-radius: var(--radius-md);
}

.account-summary strong,
.account-summary small {
  display: block;
}

.account-summary small {
  max-width: 195px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-dropdown a,
.account-dropdown button {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 10px;
  padding: 0 11px;
  color: var(--text-secondary);
  text-align: left;
  text-decoration: none;
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 750;
}

.account-dropdown a:hover,
.account-dropdown button:hover {
  color: var(--primary);
  background: var(--primary-soft);
}

.account-dropdown .danger-action {
  color: var(--danger);
}

.account-dropdown .danger-action:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.main {
  width: min(calc(100% - var(--sidebar-width) - 48px), var(--container-max));
  min-height: 100vh;
  margin-left: calc(var(--sidebar-width) + 24px);
  padding: calc(var(--topbar-height) + 24px) 0 48px;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

@media (prefers-reduced-motion: reduce) {
  .app *,
  .app *::before,
  .app *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media (max-width: 1024px) {
  .sidebar {
    display: none;
  }

  .topbar {
    left: 0;
  }

  .mobile-brand {
    display: flex;
    align-items: center;
    gap: 9px;
  }

  .mobile-brand strong {
    color: var(--primary);
    font-size: 17px;
  }

  .page-identity {
    display: none;
  }

  .mobile-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    min-width: 0;
  }

  .mobile-nav a {
    display: flex;
    min-height: 42px;
    align-items: center;
    gap: 6px;
    padding: 0 9px;
    color: var(--text-secondary);
    text-decoration: none;
    border-radius: var(--radius-md);
    font-size: 13px;
    font-weight: 700;
  }

  .mobile-nav a.router-link-active {
    color: var(--primary);
    background: var(--primary-soft);
  }

  .main {
    width: calc(100% - 36px);
    margin: 0 auto;
  }
}

@media (max-width: 760px) {
  .topbar {
    height: 66px;
    padding: 0 14px;
    backdrop-filter: none;
  }

  .mobile-nav {
    position: fixed;
    inset: auto 0 0;
    z-index: 35;
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0;
    min-height: 66px;
    padding: 6px max(8px, env(safe-area-inset-right)) calc(6px + env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
    background: rgba(255, 255, 255, 0.98);
    border-top: 1px solid var(--outline-variant);
    box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.06);
  }

  .mobile-nav a {
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    min-height: 52px;
    padding: 3px;
    font-size: 11px;
  }

  .account-name,
  .avatar-button > svg {
    display: none;
  }

  .avatar-button {
    min-height: 42px;
    padding: 3px;
    border: 0;
  }

  .mobile-brand .brand-mark {
    width: 36px;
    height: 36px;
  }

  .main {
    width: calc(100% - 24px);
    padding: 82px 0 calc(92px + env(safe-area-inset-bottom));
  }
}

@media (max-width: 420px) {
  .mobile-brand strong {
    display: none;
  }
}
</style>
