import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useChatSession } from './useChatSession'

const createStorage = () => {
  const store = new Map()

  return {
    getItem: vi.fn((key) => store.get(key) ?? null),
    setItem: vi.fn((key, value) => {
      store.set(key, String(value))
    }),
    removeItem: vi.fn((key) => {
      store.delete(key)
    }),
    clear: vi.fn(() => {
      store.clear()
    }),
  }
}

const mockJsonResponse = (data, ok = true) => ({
  ok,
  json: vi.fn().mockResolvedValue(data),
})

describe('useChatSession', () => {
  let localStorageMock
  let sessionStorageMock

  beforeEach(() => {
    localStorageMock = createStorage()
    sessionStorageMock = createStorage()
    vi.stubGlobal('localStorage', localStorageMock)
    vi.stubGlobal('sessionStorage', sessionStorageMock)
    vi.stubGlobal('fetch', vi.fn())
  })

  it('saves and restores the active chat session cache for the current user', async () => {
    localStorage.setItem('ragUser', JSON.stringify({ id: 7, username: 'doctor' }))

    const session = useChatSession()
    session.loadCurrentUser()
    session.activeSessionId.value = 42
    session.messages.value = [
      { id: 'user-1', role: 'user', content: '头痛三天' },
      { id: 'loading-1', role: 'assistant', type: 'loading', content: '' },
      { id: 'assistant-1', role: 'assistant', content: '建议观察并补充体温。' },
    ]

    session.saveChatCache()

    const restored = useChatSession()
    restored.loadCurrentUser()
    await expect(restored.restoreChatCache()).resolves.toBe(true)

    expect(restored.activeSessionId.value).toBe(42)
    expect(restored.messages.value).toEqual([
      { id: 'user-1', role: 'user', content: '头痛三天' },
      { id: 'loading-1', role: 'assistant', type: 'loading', content: '' },
      { id: 'assistant-1', role: 'assistant', content: '建议观察并补充体温。' },
    ])
  })

  it('marks a cached loading response as interrupted after a full page reload', async () => {
    localStorage.setItem('ragUser', JSON.stringify({ id: 7, username: 'doctor' }))

    const session = useChatSession()
    session.loadCurrentUser()
    session.messages.value = [
      { id: 'user-1', role: 'user', content: '头痛三天' },
      { id: 'loading-1', role: 'assistant', type: 'loading', content: '' },
    ]
    session.saveChatCache()

    const restored = useChatSession()
    restored.loadCurrentUser()
    await expect(restored.restoreChatCache({ markInterruptedLoading: true })).resolves.toBe(true)

    expect(restored.messages.value).toHaveLength(2)
    expect(restored.messages.value[1]).toMatchObject({
      role: 'assistant',
      error: {
        type: 'InterruptedRequest',
      },
    })
    expect(restored.messages.value[1].type).toBeUndefined()
  })

  it('clears only the current conversation state when starting a new chat', () => {
    localStorage.setItem('ragUser', JSON.stringify({ id: 8, username: 'patient' }))

    const session = useChatSession()
    session.loadCurrentUser()
    session.activeSessionId.value = 51
    session.restoreStatus.value = '已恢复历史会话 #51'
    session.messages.value = [{ id: 'user-1', role: 'user', content: '继续问' }]
    session.saveChatCache()

    session.clearCurrentConversation()

    expect(session.activeSessionId.value).toBe(null)
    expect(session.restoreStatus.value).toBe('')
    expect(session.messages.value).toEqual([])
    expect(sessionStorage.removeItem).toHaveBeenCalledWith('rag-chat-current:8')
  })

  it('loads saved conversation sessions for a logged-in user', async () => {
    localStorage.setItem('ragUser', JSON.stringify({ id: 9, username: 'patient' }))
    localStorage.setItem('ragToken', 'token-abc')
    fetch.mockResolvedValue(mockJsonResponse({
      count: 1,
      data: [{ id: 88, title: '咳嗽咨询', message_count: 4 }],
    }))

    const session = useChatSession()
    session.loadCurrentUser()
    await expect(session.loadConversationSessions()).resolves.toEqual([
      { id: 88, title: '咳嗽咨询', message_count: 4 },
    ])

    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/conversations\/sessions$/),
      {
        headers: {
          Authorization: 'Bearer token-abc',
        },
      },
    )
    expect(session.conversationSessions.value).toHaveLength(1)
    expect(session.sessionsStatus.value).toBe('')
  })

  it('explains that guests need to log in before sessions are listed', async () => {
    const session = useChatSession()

    await expect(session.loadConversationSessions()).resolves.toEqual([])

    expect(fetch).not.toHaveBeenCalled()
    expect(session.conversationSessions.value).toEqual([])
    expect(session.sessionsStatus.value).toBe('登录后会自动保存并显示历史会话。')
  })

  it('keeps visitor mode local and skips personal session loading', async () => {
    localStorage.setItem('ragGuest', 'true')

    const session = useChatSession()
    session.loadCurrentUser()
    await expect(session.loadConversationSessions()).resolves.toEqual([])

    expect(session.isGuest.value).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
    expect(session.conversationSessions.value).toEqual([])
    expect(session.sessionsStatus.value).toBe('游客模式可直接咨询，但不会保存到个人账号。')
  })

  it('restores a server conversation and maps stored messages for ChatMessage', async () => {
    localStorage.setItem('ragUser', JSON.stringify({ id: 10, username: 'patient' }))
    const scrollToBottom = vi.fn().mockResolvedValue(undefined)
    fetch.mockResolvedValue(mockJsonResponse({
      success: true,
      data: {
        id: 99,
        messages: [
          { id: 1, role: 'user', content: '布洛芬能不能吃？' },
          {
            id: 2,
            role: 'assistant',
            content: '请按说明书或医嘱使用。',
            action: 'medicine_query',
            intent: 'medicine_query',
            history_id: 123,
            retrieved_docs: [{ title: '布洛芬', doc_type: 'medicine' }],
            trace: { used_tools: ['medicine_search'] },
          },
        ],
      },
    }))

    const session = useChatSession({ scrollToBottom })
    session.loadCurrentUser()
    await session.restoreSessionFromServer(99)

    expect(session.activeSessionId.value).toBe(99)
    expect(session.messages.value).toMatchObject([
      { id: 'stored-user-1', role: 'user', content: '布洛芬能不能吃？' },
      {
        id: 'stored-assistant-2',
        role: 'assistant',
        content: '请按说明书或医嘱使用。',
        action: 'medicine_query',
        historyId: 123,
        docs: [{ title: '布洛芬', doc_type: 'medicine' }],
      },
    ])
    expect(scrollToBottom).toHaveBeenCalled()
  })
})
