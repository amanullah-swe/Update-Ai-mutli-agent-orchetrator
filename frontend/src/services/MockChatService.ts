import type { ChatEvent, ChatPayload, Source } from '../types/chat'
import { createId } from '../utils/messages'
import type { ChatService } from './chatService'

/**
 * Mock transport: a deterministic, timed canned stream so the UI is fully
 * runnable — and testable — before the backend exists.
 *
 * Behavior:
 *  - message_start → tokens (markdown with a list + code block) → sources → message_end → done
 *  - if the typed message contains "fail" or "error", a simulated failure is
 *    streamed instead (error event → done), exercising the error UI path.
 */
export class MockChatService implements ChatService {
  private readonly tokenDelayMs: number

  /** `config` lets tests speed the stream up (0 = no artificial delay). */
  constructor(config: { tokenDelayMs?: number } = {}) {
    this.tokenDelayMs = config.tokenDelayMs ?? 12
  }

  async *send(payload: ChatPayload): AsyncIterable<ChatEvent> {
    const assistantId = createId('assistant')
    yield { type: 'message_start', id: assistantId }

    if (shouldFail(payload.message)) {
      yield {
        type: 'error',
        message:
          'Mock transport: simulated failure (your message contained "fail" or "error"). Try a normal message.',
      }
      yield { type: 'done' }
      return
    }

    for (const token of tokenize(MOCK_ANSWER)) {
      if (this.tokenDelayMs > 0) await delay(this.tokenDelayMs)
      yield { type: 'token', delta: token }
    }
    yield { type: 'sources', sources: MOCK_SOURCES }
    yield { type: 'message_end', id: assistantId }
    yield { type: 'done' }
  }
}

export const MOCK_SOURCES: Source[] = [
  {
    document_id: 'doc_spec_001',
    chunk_id: 'chunk_hybrid_retrieval',
    snippet:
      'Hybrid retrieval combines dense and sparse signals so recall survives vocabulary gaps between query and document.',
    score: 0.92,
    metadata: { chunking: 'recursive', retrieval: 'hybrid' },
  },
  {
    document_id: 'doc_spec_002',
    chunk_id: 'chunk_reranking',
    snippet:
      'Reranking re-orders the retrieved candidates by a stronger relevance model before context construction.',
    score: 0.87,
    metadata: { reranking: 'cross_encoder' },
  },
]

const MOCK_ANSWER = [
  'Here is a **canned, mock answer** from the RAG pipeline:',
  '',
  '- **Hybrid retrieval** merges dense + sparse signals.',
  '- **Reranking** re-orders candidates before context construction.',
  '',
  'Example configuration:',
  '',
  '```yaml',
  'chunking:',
  '  strategy: recursive',
  'retrieval:',
  '  strategy: hybrid',
  '```',
  '',
  'Until the backend exists, this reply streams from the client-side mock.',
].join('\n')

function shouldFail(message: string): boolean {
  const lower = message.toLowerCase()
  return lower.includes('fail') || lower.includes('error')
}

/** Split into small tokens (words + trailing whitespace) to feel like streaming. */
function tokenize(text: string): string[] {
  return text.match(/\S+\s*/g) ?? [text]
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}