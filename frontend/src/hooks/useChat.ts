import { useCallback, useRef, useState } from 'react'
import type { Message } from '../types/chat'
import { createChatService, type ChatService } from '../services/chatService'
import {
  addSources,
  appendToken,
  createId,
  toAssistantMessage,
  toErrorMessage,
  toUserMessage,
} from '../utils/messages'

export interface UseChatOptions {
  /** Defaults to the configured transport (see createChatService). */
  service?: ChatService
  /**
   * Called whenever the working transcript changes, bound to the conversation
   * it belongs to (set via `send()` / `load()`).
   */
  onTranscriptChange?: (conversationId: string, messages: Message[]) => void
}

/**
 * Owns the working transcript for one conversation: appends the user message,
 * streams assistant tokens/sources via the injected ChatService, and tracks
 * loading + error state. Transport-agnostic. The current conversation is bound
 * through a ref so transcript changes always report the conversation they
 * belong to (no stale closures at call sites).
 */
export function useChat(options: UseChatOptions = {}) {
  const { service = createChatService(), onTranscriptChange } = options
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const streamingRef = useRef(false)
  const linkedConversationIdRef = useRef<string | undefined>(undefined)

  const updateMessages = useCallback(
    (updater: (prev: Message[]) => Message[]) => {
      setMessages((prev) => {
        const next = updater(prev)
        onTranscriptChange?.(linkedConversationIdRef.current ?? '', next)
        return next
      })
    },
    [onTranscriptChange],
  )

  const send = useCallback(
    async (text: string, conversationId?: string) => {
      const content = text.trim()
      if (content === '' || streamingRef.current) return
      if (conversationId) linkedConversationIdRef.current = conversationId

      streamingRef.current = true
      setIsLoading(true)
      setError(null)

      const userMessage = toUserMessage(content)
      const assistantId = createId('assistant')
      updateMessages((prev) => [...prev, userMessage, toAssistantMessage(assistantId)])

      try {
        const events = service.send({
          message: content,
          conversation_id: linkedConversationIdRef.current,
        })
        for await (const event of events) {
          switch (event.type) {
            case 'token':
              updateMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? appendToken(m, event.delta) : m)),
              )
              break
            case 'sources':
              updateMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? addSources(m, event.sources) : m)),
              )
              break
            case 'error':
              setError(event.message)
              updateMessages((prev) =>
                prev.map((m) => (m.id === assistantId ? toErrorMessage(m.id, event.message) : m)),
              )
              break
            default:
              break
          }
          if (event.type === 'done') break
        }
      } catch (err) {
        const reason = err instanceof Error ? err.message : String(err)
        setError(reason)
        updateMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? toErrorMessage(m.id, reason) : m)),
        )
      } finally {
        streamingRef.current = false
        setIsLoading(false)
      }
    },
    [service, updateMessages],
  )

  /** Bind the transcript to a conversation and replace it wholesale. */
  const load = useCallback(
    (conversationId: string, next: Message[]) => {
      if (streamingRef.current) return
      linkedConversationIdRef.current = conversationId
      updateMessages(() => next)
    },
    [updateMessages],
  )

  const reset = useCallback(() => load('', []), [load])

  return { messages, isLoading, error, send, load, reset }
}