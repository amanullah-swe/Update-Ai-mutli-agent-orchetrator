import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createChat, deleteChat, getChat, listChats, renameChat } from './chatApi'

describe('chatApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function stubResponse(body: unknown, status = 200): void {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  }

  const NOW = new Date().toISOString()

  it('maps GET /api/chats to the items array', async () => {
    const items = [
      {
        id: 'c-1',
        title: 'First',
        created_at: NOW,
        updated_at: NOW,
        message_count: 2,
        last_message_at: NOW,
      },
    ]
    stubResponse({ items, total: 1 })

    const result = await listChats()

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats',
      expect.objectContaining({ headers: { 'Content-Type': 'application/json' } }),
    )
    expect(result).toEqual(items)
  })

  it('POSTs a title to create a chat', async () => {
    stubResponse({ id: 'c-1', title: 'Hi', created_at: NOW, updated_at: NOW })

    await createChat('Hi')

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: 'Hi' }) }),
    )
  })

  it('POSTs an empty body when creating a chat without a title', async () => {
    stubResponse({ id: 'c-1', title: null, created_at: NOW, updated_at: NOW })

    await createChat()

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({}) }),
    )
  })

  it('fetches one chat with its transcript', async () => {
    const detail = {
      id: 'c-1',
      title: null,
      created_at: NOW,
      updated_at: NOW,
      messages: [
        { id: 'm-1', role: 'user', content: 'hi', created_at: NOW, sources: null, error: false },
      ],
    }
    stubResponse(detail)

    const result = await getChat('c-1')

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats/c-1',
      expect.objectContaining({ headers: { 'Content-Type': 'application/json' } }),
    )
    expect(result.messages).toHaveLength(1)
    expect(result.messages[0].content).toBe('hi')
  })

  it('PATCHes a rename', async () => {
    stubResponse({ id: 'c-1', title: 'Renamed', created_at: NOW, updated_at: NOW })

    await renameChat('c-1', 'Renamed')

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats/c-1',
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ title: 'Renamed' }) }),
    )
  })

  it('DELETEs a chat and resolves on 204 (no body to parse)', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }))

    await expect(deleteChat('c-1')).resolves.toBeUndefined()

    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      '/api/chats/c-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('surfaces the backend error detail when a delete fails', async () => {
    stubResponse({ detail: { code: 'not_found', message: 'Chat not found.' } }, 404)

    await expect(deleteChat('missing')).rejects.toThrow('Chat not found.')
  })

  it('surfaces the backend error detail message on non-2xx', async () => {
    stubResponse({ detail: { code: 'not_found', message: 'Chat not found.' } }, 404)

    await expect(getChat('missing')).rejects.toThrow('Chat not found.')
  })

  it('keeps a status-line message when the error body is not JSON', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('oops', { status: 500, statusText: 'Internal Server Error' }),
    )

    await expect(listChats()).rejects.toThrow(/500 Internal Server Error/)
  })

  it('reports a network failure as a reachability error', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('fetch failed'))

    await expect(listChats()).rejects.toThrow('Could not reach the backend. Is it running?')
  })
})