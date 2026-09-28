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

/**
 * A chat as the backend owns it (ChatOut / ChatSummary shape) plus an in-memory
 * transcript. The server is the source of truth: on selection the transcript is
 * re-fetched via GET /api/chats/{id}. `title` is nullable (the client renders a
 * placeholder and auto-titles from the first user message).
 */
export interface Conversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  message_count?: number
  last_message_at?: string | null
  messages: Message[]
}

/**
 * Discriminated union of events from the chat transport. The vocabulary matches
 * the backend's WebSocket frames (ADR-011: message_start → token* → sources →
 * message_end, plus in-band error); `done` is client-side, synthesized by
 * transports to mark the end of a turn. Unknown/invalid frames are dropped by
 * the transports, so the backend can evolve the contract without breaking this
 * client.
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