import type { ChatEvent, ChatPayload } from '../types/chat'
import { MockChatService } from './MockChatService'
import { WebSocketChatService } from './WebSocketChatService'

/**
 * Transport contract for chat. Every transport (WebSocket, mock, future)
 * implements exactly this interface; the UI and hooks never touch a concrete
 * transport — the client-side mirror of the Core Architectural Rule.
 */
export interface ChatService {
  /** Stream chat events for a payload until `done`, or an error is thrown. */
  send(payload: ChatPayload): AsyncIterable<ChatEvent>
}

/**
 * Select the transport by config (env), not by call sites.
 * `ws` → real backend (WS /api/chats/{id}/ws); anything else → mock
 * (tests, backend-less dev).
 */
export function createChatService(): ChatService {
  const transport = import.meta.env.VITE_CHAT_TRANSPORT ?? 'mock'
  if (transport === 'ws') {
    return new WebSocketChatService(import.meta.env.VITE_API_BASE_URL ?? '')
  }
  return new MockChatService()
}