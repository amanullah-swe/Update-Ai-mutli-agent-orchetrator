import { describe, expect, it } from 'vitest'
import type { ChatEvent } from '../types/chat'
import { WebSocketChatService, type WebSocketLike } from './WebSocketChatService'

interface FakeSocket extends WebSocketLike {
  sent: string[]
  closeCalls: Array<[number | undefined, string | undefined]>
}

function fakeSocket(): FakeSocket {
  const socket: FakeSocket = {
    sent: [],
    closeCalls: [],
    send(data: string) {
      this.sent.push(data)
    },
    close(code?: number, reason?: string) {
      this.closeCalls.push([code, reason])
    },
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
  }
  return socket
}

function frame(payload: unknown): { data: string } {
  return { data: JSON.stringify(payload) }
}

/** Collect a turn's events into an array, resolving when the stream ends. */
async function collect(service: WebSocketChatService, conversationId: string) {
  const events: ChatEvent[] = []
  await (async () => {
    for await (const event of service.send({ conversation_id: conversationId, message: 'hi' })) {
      events.push(event)
    }
  })()
  return events
}

describe('WebSocketChatService', () => {
  it('streams one full turn and closes the socket', async () => {
    const socket = fakeSocket()
    const opens: string[] = []
    const service = new WebSocketChatService('http://localhost:8001', (url) => {
      opens.push(url)
      return socket
    })

    const eventsPromise = collect(service, 'chat-1')

    socket.onopen?.(undefined)
    expect(socket.sent).toEqual([JSON.stringify({ type: 'user_message', content: 'hi' })])

    socket.onmessage?.(frame({ type: 'ready', chat_id: 'chat-1' }))
    socket.onmessage?.(frame({ type: 'message', message: { id: 'm-1' } }))
    socket.onmessage?.(frame({ type: 'message_start', id: 'a-1' }))
    socket.onmessage?.(frame({ type: 'token', delta: 'Hel' }))
    socket.onmessage?.(frame({ type: 'token', delta: 'lo' }))
    socket.onmessage?.(
      frame({
        type: 'sources',
        sources: [{ document_id: 'd-1', chunk_id: 'c-1', snippet: 'snippet' }],
      }),
    )
    socket.onmessage?.(frame({ type: 'message_end', id: 'a-1', message: { id: 'a-1' } }))

    const events = await eventsPromise
    expect(opens).toEqual(['ws://localhost:8001/api/chats/chat-1/ws'])
    expect(events).toEqual([
      { type: 'message_start', id: 'a-1' },
      { type: 'token', delta: 'Hel' },
      { type: 'token', delta: 'lo' },
      { type: 'sources', sources: [{ document_id: 'd-1', chunk_id: 'c-1', snippet: 'snippet' }] },
      { type: 'message_end', id: 'a-1' },
      { type: 'done' },
    ])
    expect(socket.closeCalls).toEqual([[1000, 'turn complete']])
  })

  it('surfaces an in-band error frame and ends the turn', async () => {
    const socket = fakeSocket()
    const service = new WebSocketChatService('http://localhost:8001', () => socket)

    const eventsPromise = collect(service, 'chat-1')
    socket.onopen?.(undefined)
    socket.onmessage?.(frame({ type: 'error', code: 'internal_error', message: 'boom' }))

    expect(await eventsPromise).toEqual([
      { type: 'error', message: 'boom' },
      { type: 'done' },
    ])
    expect(socket.closeCalls).toHaveLength(1)
  })

  it('throws when the socket closes before the reply completes', async () => {
    const socket = fakeSocket()
    const service = new WebSocketChatService('http://localhost:8001', () => socket)

    const promise = collect(service, 'chat-1')
    socket.onopen?.(undefined)
    socket.onclose?.({ code: 1006 })

    await expect(promise).rejects.toThrow('Chat connection closed before the reply completed')
  })

  it('ignores non-JSON frames and unknown frame types', async () => {
    const socket = fakeSocket()
    const service = new WebSocketChatService('http://localhost:8001', () => socket)

    const eventsPromise = collect(service, 'chat-1')
    socket.onopen?.(undefined)
    socket.onmessage?.({ data: 'not json' })
    socket.onmessage?.(frame({ type: 'future_feature', anything: true }))
    socket.onmessage?.(frame({ type: 'token', delta: 'ok' }))
    socket.onmessage?.(frame({ type: 'message_end', id: 'a-1' }))

    expect(await eventsPromise).toEqual([
      { type: 'token', delta: 'ok' },
      { type: 'message_end', id: 'a-1' },
      { type: 'done' },
    ])
  })

  it('throws before opening any socket when conversation_id is missing', async () => {
    let opened = 0
    const service = new WebSocketChatService('http://localhost:8001', () => {
      opened += 1
      return fakeSocket()
    })

    await expect(
      (async () => {
        for await (const _event of service.send({ message: 'hi' })) {
          /* not reached */
        }
      })(),
    ).rejects.toThrow('WebSocket chat requires an active conversation')

    expect(opened).toBe(0)
  })
})