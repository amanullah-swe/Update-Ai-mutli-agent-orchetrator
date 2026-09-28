import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createChat,
  deleteChat,
  listChats,
  renameChat,
  type ChatSummary,
} from '../services/chatApi'
import { toUserMessage } from '../utils/messages'
import { useConversations } from './useConversations'

vi.mock('../services/chatApi', () => ({
  listChats: vi.fn(),
  createChat: vi.fn(),
  renameChat: vi.fn(),
  deleteChat: vi.fn(),
}))

const mockListChats = vi.mocked(listChats)
const mockCreateChat = vi.mocked(createChat)
const mockRenameChat = vi.mocked(renameChat)
const mockDeleteChat = vi.mocked(deleteChat)

const NOW = new Date().toISOString()

function makeSummary(id: string, title: string | null, extra: Partial<ChatSummary> = {}): ChatSummary {
  return { id, title, created_at: NOW, updated_at: NOW, message_count: 0, last_message_at: null, ...extra }
}

describe('useConversations (server-backed)', () => {
  beforeEach(() => {
    mockListChats.mockReset()
    mockCreateChat.mockReset()
    mockRenameChat.mockReset()
    mockDeleteChat.mockReset()
    mockListChats.mockResolvedValue([])
  })

  it('hydrates the list from the server on mount', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'First'), makeSummary('c-2', null)])

    const { result } = renderHook(() => useConversations())

    await waitFor(() => expect(result.current.conversations).toHaveLength(2))
    expect(result.current.conversations[0].id).toBe('c-1')
    expect(result.current.conversations[1].title).toBeNull()
    expect(result.current.activeId).toBeNull()
  })

  it('creates a chat on the server, prepends it, and selects it', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'Old')])
    mockCreateChat.mockResolvedValue({ id: 'c-2', title: null, created_at: NOW, updated_at: NOW })

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))

    await act(async () => {
      await result.current.createConversation()
    })

    expect(mockCreateChat).toHaveBeenCalledWith()
    expect(result.current.conversations).toHaveLength(2)
    expect(result.current.conversations[0].id).toBe('c-2')
    expect(result.current.activeConversation?.id).toBe('c-2')
  })

  it('renames a chat via PATCH and reflects the server response locally', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'Old')])
    mockRenameChat.mockResolvedValue({ id: 'c-1', title: 'Renamed', created_at: NOW, updated_at: NOW })

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))

    await act(async () => {
      await result.current.renameConversation('c-1', 'Renamed')
    })

    expect(mockRenameChat).toHaveBeenCalledWith('c-1', 'Renamed')
    expect(result.current.conversations[0].title).toBe('Renamed')
  })

  it('keeps the in-memory transcript purely client-side (no server call)', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'First')])

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))

    act(() => {
      result.current.updateMessageList('c-1', [toUserMessage('hi there')])
    })

    expect(result.current.conversations[0].messages[0].content).toBe('hi there')
    expect(mockCreateChat).not.toHaveBeenCalled()
  })

  it('surfaces a list-fetch error', async () => {
    mockListChats.mockRejectedValue(new Error('backend down'))

    const { result } = renderHook(() => useConversations())

    await waitFor(() => expect(result.current.error).toBe('backend down'))
    expect(result.current.conversations).toHaveLength(0)
    expect(result.current.loading).toBe(false)
  })

  it('deletes a chat via the server and clears the selection when it was active', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'First'), makeSummary('c-2', 'Second')])
    mockDeleteChat.mockResolvedValue(undefined)

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(2))

    act(() => result.current.selectConversation('c-1'))

    let ok = false
    await act(async () => {
      ok = await result.current.deleteConversation('c-1')
    })

    expect(mockDeleteChat).toHaveBeenCalledWith('c-1')
    expect(ok).toBe(true)
    expect(result.current.conversations.map((c) => c.id)).toEqual(['c-2'])
    expect(result.current.activeId).toBeNull()
    expect(result.current.activeConversation).toBeNull()
  })

  it('keeps the selection when deleting a non-active chat', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'First'), makeSummary('c-2', 'Second')])
    mockDeleteChat.mockResolvedValue(undefined)

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(2))

    act(() => result.current.selectConversation('c-1'))

    await act(async () => {
      await result.current.deleteConversation('c-2')
    })

    expect(result.current.conversations.map((c) => c.id)).toEqual(['c-1'])
    expect(result.current.activeId).toBe('c-1')
  })

  it('keeps the list and surfaces an error when a delete fails', async () => {
    mockListChats.mockResolvedValue([makeSummary('c-1', 'First')])
    mockDeleteChat.mockRejectedValue(new Error('Chat not found.'))

    const { result } = renderHook(() => useConversations())
    await waitFor(() => expect(result.current.conversations).toHaveLength(1))

    let ok = true
    await act(async () => {
      ok = await result.current.deleteConversation('c-1')
    })

    expect(ok).toBe(false)
    expect(result.current.conversations).toHaveLength(1)
    expect(result.current.error).toBe('Chat not found.')
  })
})