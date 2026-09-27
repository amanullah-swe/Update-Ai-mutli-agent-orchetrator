import { useCallback, useEffect, useState } from 'react'
import type { Conversation, Message } from '../types/chat'
import { conversationTitle, createId, nowIso } from '../utils/messages'

const STORAGE_KEY = 'rag-chat.conversations.v1'

/**
 * Conversation list + selection, persisted locally (localStorage) until the
 * backend owns conversations. All updates are immutable; writes are guarded so
 * a throwing/quota-limited localStorage never breaks the UI.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations)
  const [activeId, setActiveId] = useState<string | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
    } catch {
      /* private mode / quota — keep state in memory only */
    }
  }, [conversations])

  const createConversation = useCallback((): Conversation => {
    const conversation: Conversation = {
      id: createId('conv'),
      title: 'New conversation',
      created_at: nowIso(),
      messages: [],
    }
    setConversations((prev) => [conversation, ...prev])
    setActiveId(conversation.id)
    return conversation
  }, [])

  const selectConversation = useCallback((id: string) => setActiveId(id), [])

  const updateMessageList = useCallback((id: string, messages: Message[]) => {
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id !== id) return c
        const firstUser = messages.find((m) => m.role === 'user')
        const title =
          c.title === 'New conversation' && firstUser
            ? conversationTitle(firstUser.content)
            : c.title
        return { ...c, title, messages }
      }),
    )
  }, [])

  const renameConversation = useCallback((id: string, title: string) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)))
  }, [])

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null

  return {
    conversations,
    activeConversation,
    activeId,
    createConversation,
    selectConversation,
    updateMessageList,
    renameConversation,
  }
}

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isConversation)
  } catch {
    return []
  }
}

function isConversation(value: unknown): value is Conversation {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.id === 'string' &&
    typeof record.title === 'string' &&
    typeof record.created_at === 'string' &&
    Array.isArray(record.messages)
  )
}