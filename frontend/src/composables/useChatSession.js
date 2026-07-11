import { computed, ref } from 'vue'
import { apiUrl } from '../api'

const CHAT_CACHE_VERSION = 3

export const useChatSession = ({ scrollToBottom } = {}) => {
  const messages = ref([])
  const currentUser = ref(null)
  const activeSessionId = ref(null)
  const conversationSessions = ref([])
  const sessionsLoading = ref(false)
  const sessionsStatus = ref('')
  const restoringSession = ref(false)
  const restoreStatus = ref('')

  const isAdmin = computed(() => currentUser.value?.role === 'admin')

  const chatCacheKey = computed(() => {
    const userKey = currentUser.value?.id || currentUser.value?.username || 'guest'
    return `rag-chat-current:${userKey}`
  })

  const authHeaders = (extra = {}) => {
    const token = localStorage.getItem('ragToken') || ''

    return {
      ...extra,
      Authorization: `Bearer ${token}`,
    }
  }

  const loadCurrentUser = () => {
    const raw = localStorage.getItem('ragUser')
    currentUser.value = raw ? JSON.parse(raw) : null
  }

  const saveChatCache = () => {
    const cache = {
      version: CHAT_CACHE_VERSION,
      activeSessionId: activeSessionId.value,
      messages: messages.value,
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
      sessionsStatus.value = '登录后会自动保存并显示历史会话。'
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

  const normalizeCachedMessages = (cachedMessages, options = {}) => {
    const { markInterruptedLoading = false } = options
    if (!Array.isArray(cachedMessages)) return []

    return cachedMessages.map((message) => {
      if (message?.type !== 'loading') return message
      if (!markInterruptedLoading) return message

      return {
        id: `assistant-interrupted-${Date.now()}`,
        role: 'assistant',
        content: '上次分析可能因页面刷新中断，请重新发送这条问题，或到历史记录中查看是否已经保存结果。',
        error: {
          type: 'InterruptedRequest',
          message: '页面刷新后，浏览器无法继续接收上一次进行中的回答。',
        },
      }
    })
  }

  const restoreChatCache = async (options = {}) => {
    const { markInterruptedLoading = false } = options
    const raw = sessionStorage.getItem(chatCacheKey.value)
    if (!raw) return false

    try {
      const cache = JSON.parse(raw)
      if (cache.version !== CHAT_CACHE_VERSION) {
        clearChatCache()
        return false
      }
      activeSessionId.value = cache.activeSessionId || null
      messages.value = normalizeCachedMessages(cache.messages, { markInterruptedLoading })
      if (markInterruptedLoading) {
        saveChatCache()
      }
      await scrollToBottom?.()
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
    activeSessionId,
    conversationSessions,
    sessionsLoading,
    sessionsStatus,
    restoreStatus,
    isAdmin,
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
