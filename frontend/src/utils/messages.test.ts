import { describe, expect, it } from 'vitest'
import type { Source } from '../types/chat'
import {
  addSources,
  appendToken,
  conversationTitle,
  createId,
  toAssistantMessage,
  toErrorMessage,
  toUserMessage,
} from './messages'

const sourceA: Source = { document_id: 'doc1', chunk_id: 'ch1', snippet: 'snippet a' }
const sourceB: Source = { document_id: 'doc1', chunk_id: 'ch2', snippet: 'snippet b' }

describe('message factories', () => {
  it('toUserMessage builds a user message', () => {
    const message = toUserMessage('hello')
    expect(message.role).toBe('user')
    expect(message.content).toBe('hello')
    expect(message.created_at).toBeTruthy()
  })

  it('toAssistantMessage starts empty', () => {
    const message = toAssistantMessage()
    expect(message.role).toBe('assistant')
    expect(message.content).toBe('')
  })

  it('toErrorMessage flags the error', () => {
    const message = toErrorMessage(undefined, '### wallet at limit')
    expect(message.error).toBe(true)
    expect(message.content).toBe('### wallet at limit')
  })

  it('createId yields unique ids', () => {
    expect(createId()).not.toBe(createId())
  })

  it('conversationTitle collapses whitespace and truncates', () => {
    expect(conversationTitle('  Hello\n world  ')).toBe('Hello world')
    const long = 'a'.repeat(100)
    expect(conversationTitle(long)).toHaveLength(49) // 48 chars + ellipsis
  })
})

describe('appendToken', () => {
  it('appends to an assistant message', () => {
    const base = toAssistantMessage()
    const next = appendToken(base, 'Hel')
    expect(next.content).toBe('Hel')
    expect(base.content).toBe('') // immutable
  })

  it('refuses to append to a user message', () => {
    const base = toUserMessage('hi')
    expect(appendToken(base, 'x').content).toBe('hi')
  })
})

describe('addSources', () => {
  it('merges sources in order', () => {
    const base = toAssistantMessage()
    const one = addSources(base, [sourceA])
    const two = addSources(one, [sourceB])
    expect(two.sources).toEqual([sourceA, sourceB])
  })

  it('de-duplicates by document/chunk id', () => {
    const base = toAssistantMessage()
    const merged = addSources(addSources(base, [sourceA]), [sourceA, sourceB])
    expect(merged.sources).toEqual([sourceA, sourceB])
  })

  it('keeps immutability', () => {
    const base = toAssistantMessage()
    const merged = addSources(base, [sourceA])
    expect(base.sources).toBeUndefined()
    expect(merged.sources).toHaveLength(1)
  })
})