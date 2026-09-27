import type { ChatEvent, ChatPayload } from '../types/chat'
import { MockChatService } from './MockChatService'
import { SseChatService } from './SseChatService'

/**
 * Transport contract for chat. Every transport (SSE, mock, future) implements
 * exactly this interface; the UI and hooks never touch a concrete transport —
 * the client-side mirror of the Core Architectural Rule.
 */
export interface ChatService {
  /** Stream chat events for a payload until `done`, or an error is thrown. */
  send(payload: ChatPayload): AsyncIterable<ChatEvent>
}

/** Select the transport by config (env), not by call sites. Defaults to mock. */
export function createChatService(): ChatService {
  const transport = import.meta.env.VITE_CHAT_TRANSPORT ?? 'mock'
  if (transport === 'sse') {
    return new SseChatService(import.meta.env.VITE_API_BASE_URL ?? '')
  }
  return new MockChatService()
}