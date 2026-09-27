/** Shared chat data contracts — the stable boundary between services, hooks, and UI. */

export type Role = 'user' | 'assistant'

/** A citation pointing back to a source document + chunk (CLAUDE.md observability). */
export interface Source {
  document_id: string
  chunk_id: string
  snippet: string
  score?: number
  metadata?: Record<string, unknown>
}

export interface Message {
  id: string
  role: Role
  content: string
  created_at: string
  sources?: Source[]
  error?: boolean
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  messages: Message[]
}

/**
 * Discriminated union of SSE frames from POST /api/chat.
 * Unknown/invalid frames are dropped by the transports, so the backend can evolve the
 * contract without breaking this client.
 */
export type ChatEvent =
  | { type: 'message_start'; id: string }
  | { type: 'token'; delta: string }
  | { type: 'sources'; sources: Source[] }
  | { type: 'message_end'; id?: string }
  | { type: 'error'; message: string }
  | { type: 'done' }

export interface ChatPayload {
  /** Opaque conversation id — echoed by the backend for tracing. */
  conversation_id?: string
  message: string
}