import type { ChatEvent, ChatPayload, Source } from '../types/chat'
import type { ChatService } from './chatService'

/**
 * The small surface of a WebSocket the transport needs — an injectable seam so
 * tests can drive a fake socket (jsdom has no WebSocket). Handler signatures
 * mirror the DOM `WebSocket` (their first argument is an `Event`-shaped value).
 */
export interface WebSocketLike {
  send(data: string): void
  close(code?: number, reason?: string): void
  onopen: ((event: unknown) => void) | null
  onmessage: ((event: { data: unknown }) => void) | null
  onclose: ((event: { code?: number; reason?: string }) => void) | null
  onerror: ((event: unknown) => void) | null
}

/** Server → client frames (backend/app/schemas/chat.py → WebSocket contract, ADR-011). */
type WsIncomingFrame =
  | { type: 'ready'; chat_id: string }
  | { type: 'message'; message: unknown }
  | { type: 'message_start'; id: string }
  | { type: 'token'; delta: string }
  | { type: 'sources'; sources: Source[] }
  | { type: 'message_end'; id: string; message: unknown }
  | { type: 'error'; code: string; message: string }

/**
 * WebSocket transport for chat (ADR-011 over `WS /api/chats/{id}/ws`).
 *
 * Implements the same `ChatService` contract as the mock: `send()` streams a
 * turn's `ChatEvent`s until completion. One socket carries one turn — opened
 * per `send()` call, closed (1000) when the turn ends. This matches the
 * backend contract, which explicitly allows multiple sockets per chat.
 *
 * Frame mapping: `ready` / `message` (server acknowledgements) are consumed
 * silently; `message_start` → `token`* → `sources`? → `message_end` map to
 * `ChatEvent`s, and the transport synthesises a client-side `done` to end the
 * stream (the socket has no `done` frame). A close before `message_end` is a
 * transport error and surfaces as a thrown `Error`.
 */
export class WebSocketChatService implements ChatService {
  private readonly baseUrl: string
  private readonly socketFactory: (url: string) => WebSocketLike

  constructor(baseUrl = '', socketFactory?: (url: string) => WebSocketLike) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    // The DOM WebSocket satisfies this narrow contract; the boundary cast keeps
    // the transport decoupled from lib.dom's `Event`-typed handler signatures.
    this.socketFactory = socketFactory ?? ((url) => new WebSocket(url) as unknown as WebSocketLike)
  }

  async *send(payload: ChatPayload): AsyncIterable<ChatEvent> {
    const chatId = payload.conversation_id
    if (!chatId) {
      throw new Error('WebSocket chat requires an active conversation (conversation_id)')
    }

    const socket = this.socketFactory(this.socketUrl(chatId))
    const queue = new SocketFrameQueue()
    let completed = false

    socket.onopen = () => {
      socket.send(JSON.stringify({ type: 'user_message', content: payload.message }))
    }
    socket.onmessage = (event) => {
      try {
        queue.push(JSON.parse(String(event.data)))
      } catch {
        /* non-JSON frame — ignore (defensive) */
      }
    }
    socket.onclose = () => queue.finish()
    socket.onerror = () => queue.finish()

    try {
      for await (const raw of queue.consume()) {
        const frame = toFrame(raw)
        if (!frame) continue

        switch (frame.type) {
          case 'ready':
          case 'message':
            continue
          case 'error':
            yield { type: 'error', message: frame.message || 'Unknown chat error' }
            yield { type: 'done' }
            completed = true
            break
          case 'message_start':
            yield { type: 'message_start', id: frame.id }
            break
          case 'token':
            yield { type: 'token', delta: frame.delta }
            break
          case 'sources':
            yield { type: 'sources', sources: frame.sources }
            break
          case 'message_end':
            yield { type: 'message_end', id: frame.id }
            yield { type: 'done' }
            completed = true
            break
          default:
            // Unknown/forward-compatible frame — ignore.
            continue
        }
        if (completed) break
      }
      if (!completed) {
        throw new Error('Chat connection closed before the reply completed')
      }
    } finally {
      socket.close(1000, 'turn complete')
      queue.finish()
    }
  }

  private socketUrl(chatId: string): string {
    const base = this.baseUrl.replace(/^http/, 'ws')
    return `${base}/api/chats/${encodeURIComponent(chatId)}/ws`
  }
}

/** Guard + narrow a JSON-parsed frame to one of the known server frames. */
function toFrame(raw: unknown): WsIncomingFrame | null {
  if (typeof raw !== 'object' || raw === null) return null
  const type = (raw as { type?: unknown }).type
  const known = new Set(['ready', 'message', 'message_start', 'token', 'sources', 'message_end', 'error'])
  return typeof type === 'string' && known.has(type) ? (raw as WsIncomingFrame) : null
}

/**
 * An async queue bridged from socket events. `push` wakes the generator's next
 * read; `finish` ends the stream (server close / error / client aborted).
 */
class SocketFrameQueue {
  private frames: unknown[] = []
  private waiters: Array<() => void> = []
  private ended = false

  push(frame: unknown): void {
    if (this.ended) return
    this.frames.push(frame)
    this.waiters.shift()?.()
  }

  finish(): void {
    if (this.ended) return
    this.ended = true
    this.waiters.shift()?.()
  }

  async *consume(): AsyncGenerator<unknown> {
    for (;;) {
      if (this.frames.length > 0) {
        yield this.frames.shift() as unknown
        continue
      }
      if (this.ended) return
      await new Promise<void>((resolve) => this.waiters.push(resolve))
    }
  }
}