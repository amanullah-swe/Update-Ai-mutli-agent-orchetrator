import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { toUserMessage } from '../utils/messages'
import { useConversations } from './useConversations'

const STORAGE_KEY = 'rag-chat.conversations.v1'

describe('useConversations', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('creates and selects a conversation', () => {
    const { result } = renderHook(() => useConversations())

    let id = ''
    act(() => {
      id = result.current.createConversation().id
    })

    expect(result.current.conversations).toHaveLength(1)
    expect(result.current.activeId).toBe(id)
    expect(result.current.activeConversation?.id).toBe(id)
  })

  it('persists conversation messages to localStorage', () => {
    const { result } = renderHook(() => useConversations())

    let id = ''
    act(() => {
      id = result.current.createConversation().id
      result.current.updateMessageList(id, [toUserMessage('hi there')])
    })

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    expect(stored).toHaveLength(1)
    expect(stored[0].messages[0].content).toBe('hi there')
    // Auto-title from the first user message.
    expect(stored[0].title).toBe('hi there')
  })

  it('hydrates existing conversations from localStorage on mount', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([
        {
          id: 'c-1',
          title: 'Old',
          created_at: new Date().toISOString(),
          messages: [toUserMessage('persisted')],
        },
      ]),
    )

    const { result } = renderHook(() => useConversations())
    expect(result.current.conversations).toHaveLength(1)
    expect(result.current.conversations[0].messages[0].content).toBe('persisted')
  })

  it('selects a conversation by id', () => {
    const { result } = renderHook(() => useConversations())

    let first = ''
    let second = ''
    act(() => {
      first = result.current.createConversation().id
      second = result.current.createConversation().id
      result.current.selectConversation(first)
    })

    expect(result.current.activeId).toBe(first)
    expect(result.current.activeConversation?.id).toBe(first)
    expect(result.current.conversations).toHaveLength(2)
    expect(result.current.conversations[0].id).toBe(second) // newest first
  })

  it('keeps a manual rename instead of the auto-title', () => {
    const { result } = renderHook(() => useConversations())

    let id: string
    act(() => {
      id = result.current.createConversation().id
      result.current.renameConversation(id, 'My important chat')
      result.current.updateMessageList(id, [toUserMessage('hello')])
    })

    expect(result.current.conversations[0].title).toBe('My important chat')
  })

  it('tolerates corrupt localStorage', () => {
    localStorage.setItem(STORAGE_KEY, '{not json')
    const { result } = renderHook(() => useConversations())
    expect(result.current.conversations).toHaveLength(0)
  })
})