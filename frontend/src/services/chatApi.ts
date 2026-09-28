import type { Message } from '../types/chat'

/**
 * Typed HTTP client for the backend chat CRUD surface (007 + 009):
 * POST /api/chats, GET /api/chats, GET /api/chats/{id}, PATCH /api/chats/{id},
 * DELETE /api/chats/{id}.
 * Errors surface the backend's `detail.message` when the body carries one.
 *
 * Wire shapes mirror the backend schemas (backend/app/schemas/chat.py); they
 * deliberately differ from `Conversation`, which additionally carries an
 * in-memory transcript.
 */
export interface ChatOut {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ChatSummary extends ChatOut {
  message_count: number
  last_message_at: string | null
}

export interface ChatDetail extends ChatOut {
  messages: Message[]
}

interface ApiErrorBody {
  detail?: { code?: string; message?: string }
}

function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
}

async function request<T>(path: string, init?: RequestInit, parseJson = true): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers as Record<string, string> | undefined) },
    })
  } catch {
    throw new Error('Could not reach the backend. Is it running?')
  }
  if (!response.ok) throw await toApiError(response)
  // 204 No Content carries no body — callers (DELETE) pass parseJson=false.
  if (!parseJson) return undefined as T
  return (await response.json()) as T
}

async function toApiError(response: Response): Promise<Error> {
  let message = `Request failed: HTTP ${response.status} ${response.statusText}`
  try {
    const body = (await response.json()) as ApiErrorBody
    if (body.detail?.message) message = body.detail.message
  } catch {
    /* non-JSON error body — keep the status-line message */
  }
  return new Error(message)
}

/** GET /api/chats — summaries, most recently active first. */
export async function listChats(): Promise<ChatSummary[]> {
  const body = await request<{ items: ChatSummary[]; total: number }>('/api/chats')
  return body.items
}

/** POST /api/chats — create a chat; `title` optional (null on creation). */
export async function createChat(title?: string | null): Promise<ChatOut> {
  return request<ChatOut>('/api/chats', {
    method: 'POST',
    body: JSON.stringify(title ? { title } : {}),
  })
}

/** GET /api/chats/{id} — one chat with its full transcript in order. */
export async function getChat(id: string): Promise<ChatDetail> {
  return request<ChatDetail>(`/api/chats/${encodeURIComponent(id)}`)
}

/** PATCH /api/chats/{id} — rename a chat (bumps `updated_at`). */
export async function renameChat(id: string, title: string): Promise<ChatOut> {
  return request<ChatOut>(`/api/chats/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

/** DELETE /api/chats/{id} — delete a chat; its messages cascade server-side. */
export async function deleteChat(id: string): Promise<void> {
  await request<void>(`/api/chats/${encodeURIComponent(id)}`, { method: 'DELETE' }, false)
}