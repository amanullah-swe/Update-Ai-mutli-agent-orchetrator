import type { Message, Source } from '../types/chat'

/** Collision-resistant-ish client id (no backend round-trip needed). */
export function createId(prefix = 'msg'): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

export function nowIso(): string {
  return new Date().toISOString()
}

export function toUserMessage(content: string): Message {
  return { id: createId('user'), role: 'user', content, created_at: nowIso() }
}

export function toAssistantMessage(id = createId('assistant')): Message {
  return { id, role: 'assistant', content: '', created_at: nowIso() }
}

export function toErrorMessage(id = createId('assistant'), reason: string): Message {
  return { id, role: 'assistant', content: reason, created_at: nowIso(), error: true }
}

/** Append a streamed token to an assistant message (immutable). */
export function appendToken(message: Message, delta: string): Message {
  if (message.role !== 'assistant') return message
  return { ...message, content: message.content + delta }
}

/** Attach sources, de-duplicated by `document_id`/`chunk_id` (immutable). */
export function addSources(message: Message, sources: Source[]): Message {
  if (sources.length === 0) return message
  const existing = new Set((message.sources ?? []).map((s) => `${s.document_id}/${s.chunk_id}`))
  const merged = [...(message.sources ?? [])]
  for (const source of sources) {
    const key = `${source.document_id}/${source.chunk_id}`
    if (!existing.has(key)) {
      existing.add(key)
      merged.push(source)
    }
  }
  return { ...message, sources: merged }
}

/** Derive a conversation title from its first user message. */
export function conversationTitle(firstUserContent: string, maxLength = 48): string {
  const singleLine = firstUserContent.replace(/\s+/g, ' ').trim()
  if (singleLine.length <= maxLength) return singleLine
  return `${singleLine.slice(0, maxLength)}…`
}