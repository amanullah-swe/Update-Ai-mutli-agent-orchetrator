import { useCallback, useEffect, useState } from 'react'
import type { Conversation, Message } from '../types/chat'
import {
  createChat,
  deleteChat,
  listChats,
  renameChat,
  type ChatOut,
  type ChatSummary,
} from '../services/chatApi'

/**
 * Conversation list + selection, backed by the chat CRUD API (007). The server
 * is the source of truth: the list is fetched on mount, creation and renaming
 * hit HTTP routes, and transcripts live server-side (re-fetched on selection —
 * see ChatPage). This hook keeps client state only for instant UI feedback:
 * ordering, selection, and an in-memory transcript used for sidebar previews.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  // Start in the loading state: the first fetch is kicked off by the effect below.
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch the chat list once on mount (server is the source of truth).
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const items = await listChats()
        if (cancelled) return
        setConversations(items.map(toConversation))
        setError(null)
      } catch (err) {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  /** POST /api/chats — returns the new conversation, or null on failure. */
  const createConversation = useCallback(async (): Promise<Conversation | null> => {
    setError(null)
    try {
      const chat = await createChat()
      const conversation = toConversation({ ...chat, message_count: 0, last_message_at: null })
      setConversations((prev) => [conversation, ...prev])
      setActiveId(conversation.id)
      return conversation
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      return null
    }
  }, [])

  const selectConversation = useCallback((id: string) => setActiveId(id), [])

  /** Keep the in-memory transcript (sidebar preview) — never persisted client-side. */
  const updateMessageList = useCallback((id: string, messages: Message[]) => {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, messages } : c)))
  }, [])

  /** PATCH /api/chats/{id} — rename on the server, then reflect it locally. */
  const renameConversation = useCallback(async (id: string, title: string) => {
    setError(null)
    try {
      const chat = await renameChat(id, title)
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, title: chat.title, updated_at: chat.updated_at } : c,
        ),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [])

  /**
   * DELETE /api/chats/{id} — remove on the server, then drop it locally. If the
   * deleted chat was the active one, the selection clears. Returns success so
   * callers can reset the transcript.
   */
  const deleteConversation = useCallback(async (id: string): Promise<boolean> => {
    setError(null)
    try {
      await deleteChat(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      setActiveId((current) => (current === id ? null : current))
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      return false
    }
  }, [])

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null

  return {
    conversations,
    activeConversation,
    activeId,
    loading,
    error,
    createConversation,
    selectConversation,
    updateMessageList,
    renameConversation,
    deleteConversation,
  }
}

function toConversation(summary: ChatSummary | ChatOut): Conversation {
  const isSummary = 'message_count' in summary
  return {
    id: summary.id,
    title: summary.title,
    created_at: summary.created_at,
    updated_at: summary.updated_at,
    message_count: isSummary ? summary.message_count : 0,
    last_message_at: isSummary ? summary.last_message_at : null,
    messages: [],
  }
}