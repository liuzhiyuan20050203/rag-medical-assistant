import { computed, ref } from 'vue'
import { apiUrl } from '../api'

export const useChatSession = ({ scrollToBottom } = {}) => {
  const messages = ref([])
  const currentUser = ref(null)
  const guestMode = ref(false)
  const activeSessionId = ref(null)
  const conversationSessions = ref([])
  const sessionsLoading = ref(false)
  const sessionsStatus = ref('')
  const restoringSession = ref(false)
  const restoreStatus = ref('')

  const isAdmin = computed(() => currentUser.value?.role === 'admin')
  const isGuest = computed(() => !currentUser.value && guestMode.value)

  const chatCacheKey = computed(() => {
    const userKey = currentUser.value?.id || currentUser.value?.username || 'guest'
    return `rag-chat-current:${userKey}`
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

  const loadCurrentUser = () => {
    const raw = localStorage.getItem('ragUser')
    currentUser.value = raw ? JSON.parse(raw) : null
    guestMode.value = !currentUser.value && localStorage.getItem('ragGuest') === 'true'
  }

  const saveChatCache = () => {
    const cache = {
      activeSessionId: activeSessionId.value,
      messages: messages.value.filter((message) => message.type !== 'loading'),
      savedAt: Date.now(),
    }
    sessionStorage.setItem(chatCacheKey.value, JSON.stringify(cache))
  }

  const clearChatCache = () => {
    sessionStorage.removeItem(chatCacheKey.value)
  }

  const clearCurrentConversation = () => {
    messages.value = []
    activeSessionId.value = null
    restoreStatus.value = ''
    clearChatCache()
  }

  const loadConversationSessions = async () => {
    if (!currentUser.value) {
      conversationSessions.value = []
      sessionsStatus.value = guestMode.value
        ? '游客模式可直接咨询，但不会保存到个人账号。'
        : '登录后会自动保存并显示历史会话。'
      return []
    }

    sessionsLoading.value = true
    sessionsStatus.value = ''

    try {
      const response = await fetch(apiUrl('/api/conversations/sessions'), {
        headers: authHeaders(),
      })
      const data = await response.json()

      if (!response.ok) {
        sessionsStatus.value = data.message || '历史会话加载失败。'
        conversationSessions.value = []
        return []
      }

      conversationSessions.value = data.data || []
      sessionsStatus.value = data.message || ''
      return conversationSessions.value
    } catch (error) {
      sessionsStatus.value = '历史会话加载失败，请检查后端服务。'
      conversationSessions.value = []
      console.error(error)
      return []
    } finally {
      sessionsLoading.value = false
    }
  }

  const restoreChatCache = async () => {
    const raw = sessionStorage.getItem(chatCacheKey.value)
    if (!raw) return false

    try {
      const cache = JSON.parse(raw)
      activeSessionId.value = cache.activeSessionId || null
      messages.value = Array.isArray(cache.messages) ? cache.messages : []
      if (messages.value.length > 0) {
        await scrollToBottom?.()
      }
      return messages.value.length > 0
    } catch (error) {
      clearChatCache()
      console.error(error)
      return false
    }
  }

  const mapStoredMessage = (message) => {
    if (message.role === 'user') {
      return {
        id: `stored-user-${message.id}`,
        role: 'user',
        content: message.content || '',
      }
    }

    return {
      id: `stored-assistant-${message.id}`,
      role: 'assistant',
      content: message.content || '',
      warning: message.warning || message.trace?.warning || null,
      followups: message.followup_questions || [],
      docs: message.retrieved_docs || [],
      trace: message.trace || null,
      action: message.action || '',
      intent: message.intent || message.trace?.intent || '',
      confidence: message.confidence ?? message.trace?.confidence ?? null,
      reliability: message.reliability || message.trace?.reliability || null,
      error: null,
      historyId: message.history_id || null,
      feedbackType: '',
      feedbackStatus: '',
      feedbackLoading: false,
    }
  }

  const restoreSessionFromServer = async (sessionId) => {
    if (!sessionId || restoringSession.value) return

    restoringSession.value = true
    restoreStatus.value = '正在恢复历史会话...'

    try {
      const response = await fetch(apiUrl(`/api/conversations/${sessionId}`), {
        headers: authHeaders(),
      })
      const data = await response.json()

      if (!response.ok || !data.success) {
        restoreStatus.value = data.message || '历史会话恢复失败。'
        return
      }

      const detail = data.data || {}
      activeSessionId.value = detail.id || Number(sessionId)
      messages.value = (detail.messages || []).map(mapStoredMessage).filter((item) => item.content)
      saveChatCache()
      restoreStatus.value = `已恢复历史会话 #${activeSessionId.value}`
      await scrollToBottom?.()
    } catch (error) {
      restoreStatus.value = '历史会话恢复失败，请检查后端服务。'
      console.error(error)
    } finally {
      restoringSession.value = false
    }
  }

  return {
    messages,
    currentUser,
    guestMode,
    activeSessionId,
    conversationSessions,
    sessionsLoading,
    sessionsStatus,
    restoreStatus,
    isAdmin,
    isGuest,
    authHeaders,
    loadCurrentUser,
    saveChatCache,
    clearChatCache,
    clearCurrentConversation,
    loadConversationSessions,
    restoreChatCache,
    restoreSessionFromServer,
  }
}
