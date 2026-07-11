<template>
  <div class="profile-page">
    <section class="profile-heading ui-page-heading">
      <h2>个人设置</h2>
      <p>管理头像、昵称、个人基本资料和账号密码。资料会用于右上角用户菜单和个人会话显示。</p>
    </section>

    <section v-if="!isLoggedIn" class="access-panel ui-card">
      <div>
        <span class="eyebrow">ACCOUNT REQUIRED</span>
        <h3>请先登录账号</h3>
        <p>游客可以直接体验咨询，但个人资料、头像和密码设置需要登录后使用。</p>
      </div>
      <div class="access-actions">
        <RouterLink class="ui-button ui-button--primary" to="/login">去登录</RouterLink>
        <RouterLink class="ui-button ui-button--soft" to="/register">注册账号</RouterLink>
      </div>
    </section>

    <template v-else>
      <section class="profile-summary ui-card">
        <div class="avatar-preview">
          <img v-if="profile.avatar" :src="profile.avatar" alt="当前头像" />
          <span v-else>{{ avatarText }}</span>
        </div>
        <div>
          <span class="eyebrow">MY ACCOUNT</span>
          <h3>{{ profile.display_name || profile.username }}</h3>
          <p>{{ profile.role === 'admin' ? '管理员账号' : '普通用户账号' }} · {{ profile.username }}</p>
        </div>
      </section>

      <section class="settings-grid">
        <form class="settings-panel ui-card" @submit.prevent="saveProfile">
          <div class="panel-title">
            <div>
              <h3>头像与基本资料</h3>
              <p>修改后会立即同步到右上角用户菜单。</p>
            </div>
          </div>

          <div class="avatar-editor">
            <div class="avatar-preview large">
              <img v-if="profile.avatar" :src="profile.avatar" alt="待保存头像" />
              <span v-else>{{ avatarText }}</span>
            </div>

            <div class="avatar-actions">
              <input
                ref="avatarInputRef"
                type="file"
                accept="image/*"
                class="sr-only"
                @change="handleAvatarFile"
              />
              <button type="button" class="ui-button ui-button--soft" @click="avatarInputRef?.click()">
                <Upload :size="17" aria-hidden="true" />
                更改头像
              </button>
              <button type="button" class="ui-button" :disabled="!profile.avatar" @click="clearAvatar">
                <Trash2 :size="17" aria-hidden="true" />
                清除头像
              </button>
            </div>
          </div>

          <div class="form-grid">
            <label class="field">
              <span>用户名</span>
              <input v-model.trim="profile.username" class="ui-field" autocomplete="username" />
            </label>

            <label class="field">
              <span>昵称</span>
              <input v-model.trim="profile.display_name" class="ui-field" placeholder="用于页面展示的名字" />
            </label>

            <label class="field">
              <span>真实姓名</span>
              <input v-model.trim="profile.real_name" class="ui-field" placeholder="选填" />
            </label>

            <label class="field">
              <span>邮箱</span>
              <input v-model.trim="profile.email" class="ui-field" type="email" placeholder="name@example.com" />
            </label>

            <label class="field">
              <span>电话</span>
              <input v-model.trim="profile.phone" class="ui-field" inputmode="tel" placeholder="选填" />
            </label>

            <label class="field">
              <span>性别</span>
              <select v-model="profile.gender" class="ui-field">
                <option value="">不填写</option>
                <option value="男">男</option>
                <option value="女">女</option>
                <option value="其他">其他</option>
              </select>
            </label>

            <label class="field">
              <span>生日</span>
              <input v-model="profile.birthday" class="ui-field" type="date" />
            </label>

            <label class="field field-wide">
              <span>个人简介</span>
              <textarea
                v-model.trim="profile.bio"
                class="ui-textarea"
                maxlength="200"
                placeholder="可以写一点个人说明，最多 200 字。"
              ></textarea>
            </label>
          </div>

          <p v-if="profileStatus" :class="['status-message', profileSuccess ? 'success' : 'error']">
            {{ profileStatus }}
          </p>

          <button class="ui-button ui-button--primary save-btn" type="submit" :disabled="profileSaving">
            <Save :size="17" aria-hidden="true" />
            {{ profileSaving ? '保存中...' : '保存资料' }}
          </button>
        </form>

        <form class="settings-panel ui-card" @submit.prevent="changePassword">
          <div class="panel-title">
            <div>
              <h3>修改密码</h3>
              <p>密码至少 6 位，修改后当前登录状态仍会保留。</p>
            </div>
          </div>

          <label class="field">
            <span>当前密码</span>
            <input v-model="passwordForm.oldPassword" class="ui-field" type="password" autocomplete="current-password" />
          </label>

          <label class="field">
            <span>新密码</span>
            <input v-model="passwordForm.newPassword" class="ui-field" type="password" autocomplete="new-password" />
          </label>

          <label class="field">
            <span>确认新密码</span>
            <input v-model="passwordForm.confirmPassword" class="ui-field" type="password" autocomplete="new-password" />
          </label>

          <p v-if="passwordStatus" :class="['status-message', passwordSuccess ? 'success' : 'error']">
            {{ passwordStatus }}
          </p>

          <button class="ui-button ui-button--primary save-btn" type="submit" :disabled="passwordSaving">
            <KeyRound :size="17" aria-hidden="true" />
            {{ passwordSaving ? '修改中...' : '修改密码' }}
          </button>
        </form>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { KeyRound, Save, Trash2, Upload } from '@lucide/vue'
import { apiUrl } from '../api'

const route = useRoute()
const router = useRouter()
const avatarInputRef = ref(null)
const isLoggedIn = ref(false)
const profileSaving = ref(false)
const passwordSaving = ref(false)
const profileStatus = ref('')
const passwordStatus = ref('')
const profileSuccess = ref(false)
const passwordSuccess = ref(false)

const emptyProfile = () => ({
  username: '',
  display_name: '',
  real_name: '',
  email: '',
  phone: '',
  gender: '',
  birthday: '',
  bio: '',
  avatar: '',
  role: 'user',
})

const profile = reactive(emptyProfile())
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const avatarText = computed(() => {
  const text = profile.display_name || profile.username || '用户'
  return text.slice(0, 2).toUpperCase()
})

const authHeaders = (extra = {}) => {
  const token = localStorage.getItem('ragToken') || ''

  return token
    ? {
        ...extra,
        Authorization: `Bearer ${token}`,
      }
    : { ...extra }
}

const syncUser = (user) => {
  if (!user) return
  localStorage.setItem('ragUser', JSON.stringify(user))
  localStorage.removeItem('ragGuest')
  window.dispatchEvent(new Event('rag-user-change'))
}

const fillProfile = (user = {}) => {
  Object.assign(profile, emptyProfile(), user)
  profile.display_name = profile.display_name || profile.username
}

const loadProfile = async () => {
  const token = localStorage.getItem('ragToken')
  const rawUser = localStorage.getItem('ragUser')

  isLoggedIn.value = Boolean(token && rawUser)

  if (!isLoggedIn.value) {
    router.replace({
      path: '/login',
      query: {
        redirect: route.fullPath,
      },
    })
    return
  }

  if (rawUser) {
    try {
      fillProfile(JSON.parse(rawUser))
    } catch (error) {
      console.error(error)
    }
  }

  try {
    const response = await fetch(apiUrl('/api/auth/me'), {
      headers: authHeaders(),
    })
    const data = await response.json()

    if (!response.ok || !data.success) {
      localStorage.removeItem('ragUser')
      localStorage.removeItem('ragToken')
      window.dispatchEvent(new Event('rag-user-change'))
      router.replace({
        path: '/login',
        query: {
          redirect: route.fullPath,
        },
      })
      return
    }

    fillProfile(data.user)
    syncUser(data.user)
  } catch (error) {
    profileStatus.value = '个人资料加载失败，请检查后端服务。'
    profileSuccess.value = false
    console.error(error)
  }
}

const resizeAvatar = (file, size = 240, quality = 0.82) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const image = new window.Image()
      image.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = size
        canvas.height = size
        const context = canvas.getContext('2d')
        const scale = Math.max(size / image.width, size / image.height)
        const width = image.width * scale
        const height = image.height * scale
        const x = (size - width) / 2
        const y = (size - height) / 2
        context.drawImage(image, x, y, width, height)
        resolve(canvas.toDataURL('image/jpeg', quality))
      }
      image.onerror = () => reject(new Error('图片解码失败'))
      image.src = String(reader.result || '')
    }
    reader.onerror = () => reject(new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })

const handleAvatarFile = async (event) => {
  const file = event.target.files?.[0]
  event.target.value = ''

  if (!file) return

  if (!String(file.type || '').startsWith('image/')) {
    profileStatus.value = '请选择图片文件作为头像。'
    profileSuccess.value = false
    return
  }

  try {
    profile.avatar = await resizeAvatar(file)
    profileStatus.value = '头像已更新预览，保存后生效。'
    profileSuccess.value = true
  } catch (error) {
    profileStatus.value = error.message || '头像处理失败，请重新选择图片。'
    profileSuccess.value = false
  }
}

const clearAvatar = () => {
  profile.avatar = ''
  profileStatus.value = '头像已清除，保存后生效。'
  profileSuccess.value = true
}

const validateProfile = () => {
  if (!profile.username.trim() || profile.username.trim().length < 3) {
    return '用户名至少 3 位。'
  }

  if (!profile.display_name.trim()) {
    return '请填写昵称。'
  }

  return ''
}

const saveProfile = async () => {
  const validationMessage = validateProfile()
  if (validationMessage) {
    profileStatus.value = validationMessage
    profileSuccess.value = false
    return
  }

  profileSaving.value = true
  profileStatus.value = ''

  try {
    const response = await fetch(apiUrl('/api/auth/profile'), {
      method: 'PUT',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify(profile),
    })
    const data = await response.json()

    profileStatus.value = data.message || (data.success ? '个人资料已保存。' : '个人资料保存失败。')
    profileSuccess.value = Boolean(data.success)

    if (data.success && data.user) {
      fillProfile(data.user)
      syncUser(data.user)
    }
  } catch (error) {
    profileStatus.value = '保存失败，请检查后端服务。'
    profileSuccess.value = false
    console.error(error)
  } finally {
    profileSaving.value = false
  }
}

const changePassword = async () => {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    passwordStatus.value = '请填写当前密码和新密码。'
    passwordSuccess.value = false
    return
  }

  if (passwordForm.newPassword.length < 6) {
    passwordStatus.value = '新密码至少 6 位。'
    passwordSuccess.value = false
    return
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordStatus.value = '两次输入的新密码不一致。'
    passwordSuccess.value = false
    return
  }

  passwordSaving.value = true
  passwordStatus.value = ''

  try {
    const response = await fetch(apiUrl('/api/auth/password'), {
      method: 'PUT',
      headers: authHeaders({
        'Content-Type': 'application/json',
      }),
      body: JSON.stringify({
        old_password: passwordForm.oldPassword,
        new_password: passwordForm.newPassword,
      }),
    })
    const data = await response.json()

    passwordStatus.value = data.message || (data.success ? '密码已修改。' : '密码修改失败。')
    passwordSuccess.value = Boolean(data.success)

    if (data.success) {
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
      if (data.user) {
        syncUser(data.user)
      }
    }
  } catch (error) {
    passwordStatus.value = '修改失败，请检查后端服务。'
    passwordSuccess.value = false
    console.error(error)
  } finally {
    passwordSaving.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.profile-page {
  display: grid;
  gap: 20px;
}

.profile-heading {
  margin-bottom: 0;
}

.access-panel,
.profile-summary,
.settings-panel {
  padding: 24px;
}

.access-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
}

.access-panel h3,
.profile-summary h3,
.panel-title h3 {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 900;
}

.access-panel p,
.profile-summary p,
.panel-title p {
  margin-top: 6px;
  color: var(--text-secondary);
  line-height: 1.75;
}

.access-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.eyebrow {
  color: var(--pharmacy-teal);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
}

.profile-summary {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  display: grid;
  flex: 0 0 auto;
  width: 70px;
  height: 70px;
  place-items: center;
  overflow: hidden;
  color: #ffffff;
  background: linear-gradient(135deg, var(--medical-blue), var(--clinical-green));
  border-radius: 999px;
  font-size: 22px;
  font-weight: 900;
  box-shadow: 0 14px 26px rgba(37, 99, 235, 0.18);
}

.avatar-preview.large {
  width: 96px;
  height: 96px;
  font-size: 30px;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.settings-panel {
  display: grid;
  gap: 18px;
}

.panel-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.avatar-editor {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 16px;
  background: #f8fbfd;
  border: 1px solid #e4edf3;
  border-radius: 8px;
}

.avatar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.avatar-actions .ui-button,
.save-btn {
  gap: 7px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  white-space: nowrap;
  border: 0;
  clip: rect(0 0 0 0);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: grid;
  gap: 7px;
  color: var(--text-primary);
  font-weight: 900;
}

.field span {
  font-size: 14px;
}

.field-wide {
  grid-column: 1 / -1;
}

.field select {
  appearance: none;
}

.status-message {
  padding: 11px 12px;
  border-radius: 8px;
  font-weight: 800;
}

.status-message.success {
  color: var(--success-text);
  background: var(--success-soft);
  border: 1px solid var(--success-border);
}

.status-message.error {
  color: #991b1b;
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
}

.save-btn {
  justify-self: start;
  min-height: 42px;
}

@media (max-width: 980px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .access-panel,
  .profile-summary,
  .avatar-editor {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
