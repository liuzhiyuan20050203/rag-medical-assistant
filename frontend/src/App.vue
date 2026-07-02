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
          <strong>RAG 智慧医疗助手</strong>
          <small>常见病自查与用药指南</small>
        </span>
      </RouterLink>

      <nav class="nav" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/chat">症状自查</RouterLink>
        <RouterLink to="/medicine">用药查询</RouterLink>
        <RouterLink to="/multimodal">多模态识别</RouterLink>
        <RouterLink to="/knowledge">知识库</RouterLink>
        <RouterLink to="/history">历史记录</RouterLink>
        <RouterLink to="/analytics">可视化分析</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin">管理后台</RouterLink>
        <RouterLink to="/login">登录/注册</RouterLink>
      </nav>
    </header>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const currentUser = ref(null)

const loadCurrentUser = () => {
  const raw = localStorage.getItem('ragUser')
  currentUser.value = raw ? JSON.parse(raw) : null
}

const isAdmin = computed(() => currentUser.value?.role === 'admin')

onMounted(() => {
  loadCurrentUser()
  window.addEventListener('storage', loadCurrentUser)
  window.addEventListener('rag-user-change', loadCurrentUser)
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', loadCurrentUser)
  window.removeEventListener('rag-user-change', loadCurrentUser)
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

.main {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 34px 0 56px;
}

@media (max-width: 860px) {
  .header {
    position: static;
    align-items: flex-start;
    flex-direction: column;
  }

  .brand {
    min-width: 0;
  }

  .nav {
    justify-content: flex-start;
    width: 100%;
  }

  .nav a {
    flex: 1 1 120px;
    justify-content: center;
  }
}
</style>
