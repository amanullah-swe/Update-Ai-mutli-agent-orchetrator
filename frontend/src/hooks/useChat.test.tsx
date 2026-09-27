import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MockChatService } from '../services/MockChatService'
import { useChat } from './useChat'

function mockService(delayMs = 0): MockChatService {
  return new MockChatService({ tokenDelayMs: delayMs })
}

describe('useChat', () => {
  it('streams a reply end-to-end and persists transcript changes', async () => {
    const transcripts: string[][] = []
    const { result } = renderHook(() =>
      useChat({
        service: mockService(),
        onTranscriptChange: (_conversationId, messages) =>
          transcripts.push(messages.map((m) => `${m.role}:${m.content}`)),
      }),
    )

    expect(result.current.isLoading).toBe(false)

    await act(async () => {
      await result.current.send('hello', 'conv-1')
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()

    const messages = result.current.messages
    expect(messages).toHaveLength(2) // user + assistant
    expect(messages[0].role).toBe('user')
    expect(messages[0].content).toBe('hello')
    expect(messages[1].role).toBe('assistant')
    expect(messages[1].content).toContain('**canned, mock answer**')
    expect(messages[1].content).toContain('```yaml')
    expect(messages[1].sources).toHaveLength(2)

    // Transcript change callback receives the bound conversation id.
    expect(transcripts.length).toBeGreaterThan(0)
    expect(transcripts[transcripts.length - 1]).toContain('user:hello')
  })

  it('surfaces a streamed error event on the assistant message', async () => {
    const { result } = renderHook(() => useChat({ service: mockService() }))

    await act(async () => {
      await result.current.send('please make this fail', 'conv-2')
    })

    expect(result.current.error).toContain('simulated failure')
    const last = result.current.messages.at(-1)
    expect(last?.error).toBe(true)
  })

  it('converts a thrown transport error into a message error', async () => {
    const failingService = {
      send: async function* () {
        yield { type: 'token' as const, delta: 'partial' }
        throw new Error('backend unreachable')
      },
    }
    const { result } = renderHook(() => useChat({ service: failingService }))

    await act(async () => {
      await result.current.send('hi', 'conv-3')
    })

    expect(result.current.error).toBe('backend unreachable')
    expect(result.current.messages.at(-1)?.error).toBe(true)
  })

  it('ignores empty input', async () => {
    const { result } = renderHook(() => useChat({ service: mockService() }))
    await act(async () => {
      await result.current.send('   ', 'conv-4')
    })
    expect(result.current.messages).toHaveLength(0)
    expect(result.current.isLoading).toBe(false)
  })

  it('rejects concurrent sends while streaming', async () => {
    const { result } = renderHook(() => useChat({ service: mockService(1) }))

    let first!: Promise<void>
    await act(async () => {
      first = result.current.send('one', 'conv-5')
      // Second send is a no-op while the first is still streaming.
      await result.current.send('two', 'conv-5')
    })
    // Let the first stream complete.
    await act(async () => {
      await first
    })

    const userMessages = result.current.messages.filter((m) => m.role === 'user')
    expect(userMessages).toHaveLength(1)
    expect(userMessages[0].content).toBe('one')
  })
})