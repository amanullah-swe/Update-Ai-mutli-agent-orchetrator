import type { ChatEvent, ChatPayload, Source } from '../types/chat'
import { isDoneFrame, type SseFrame } from '../utils/sse'
import { readSseStream } from './sseClient'
import type { ChatService } from './chatService'

/**
 * SSE transport: drives `POST /api/chat` and maps raw `SseFrame`s to
 * `ChatEvent`s. Unknown event names are dropped rather than fatal, so the
 * backend's frame names can evolve without breaking the client.
 */
export class SseChatService implements ChatService {
  private readonly baseUrl: string

  constructor(baseUrl = '') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
  }

  async *send(payload: ChatPayload): AsyncIterable<ChatEvent> {
    const url = `${this.baseUrl}/api/chat`
    for await (const frame of readSseStream(url, payload)) {
      const event = frameToChatEvent(frame)
      if (event) yield event
    }
  }
}

function frameToChatEvent(frame: SseFrame): ChatEvent | null {
  if (isDoneFrame(frame)) return { type: 'done' }

  const data = frame.data.trim()
  switch (frame.event) {
    case 'message_start':
      return { type: 'message_start', id: data }
    case 'token':
      return { type: 'token', delta: data }
    case 'sources': {
      const sources = parseSources(data)
      return sources ? { type: 'sources', sources } : null
    }
    case 'message_end':
      return { type: 'message_end', id: data || undefined }
    case 'error':
      return { type: 'error', message: data || 'Unknown chat error' }
    case 'done':
      return { type: 'done' }
    default:
      // Unknown/forward-compatible event type — ignore.
      return null
  }
}

/** Accept either a bare Source[] or an object with a `sources` field. */
function parseSources(data: string): Source[] | null {
  try {
    const parsed: unknown = JSON.parse(data)
    const sources = Array.isArray(parsed) ? parsed : (parsed as { sources?: unknown })?.sources
    if (!Array.isArray(sources)) return null
    return sources.filter(isSource)
  } catch {
    return null
  }
}

function isSource(value: unknown): value is Source {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.document_id === 'string' &&
    typeof record.chunk_id === 'string' &&
    typeof record.snippet === 'string'
  )
}