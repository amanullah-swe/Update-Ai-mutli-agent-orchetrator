import { parseSseStream, type SseFrame } from '../utils/sse'

/**
 * Low-level SSE reader: POST a JSON payload to `url` and consume the
 * `text/event-stream` body as `SseFrame`s, incrementally.
 *
 * Uses `fetch` + `ReadableStream` (NOT `EventSource`) because the backend
 * contract is `POST /api/chat` — EventSource cannot send a request body.
 */
export async function* readSseStream(
  url: string,
  payload: unknown,
  init?: { headers?: Record<string, string> },
): AsyncGenerator<SseFrame> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...init?.headers,
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    throw new Error(`Chat request failed: HTTP ${response.status} ${response.statusText}`)
  }
  if (!response.body) {
    throw new Error('Chat response has no body stream')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { frames, rest } = parseSseStream(buffer)
      buffer = rest
      for (const frame of frames) yield frame
    }
    buffer += decoder.decode()
    const { frames } = parseSseStream(buffer)
    for (const frame of frames) yield frame
  } finally {
    reader.releaseLock()
  }
}