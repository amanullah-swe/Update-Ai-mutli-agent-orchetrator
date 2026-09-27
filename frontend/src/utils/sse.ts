/**
 * Incremental SSE parser (pure — no DOM/fetch).
 *
 * Consumes an accumulated text buffer split into `SseFrame`s whenever a blank
 * line terminates an event. Any trailing partial data is returned as `rest`,
 * ready for the next chunk. Tolerates garbage: comment lines (`: ...`) and
 * unknown fields are ignored, so a backend that adds fields never breaks this.
 */

export const SSE_DONE = '[DONE]'

export interface SseFrame {
  /** Event type — "message" when the `event:` field is absent. */
  event: string
  /** Payload: `data:` lines joined with `\n`. */
  data: string
}

export interface SseParseResult {
  frames: SseFrame[]
  /** Unconsumed tail of the buffer (partial event, no blank-line terminator yet). */
  rest: string
}

/** Parse one event block (everything up to a blank line). */
export function parseSseBlock(block: string): SseFrame | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      // Strip the single leading space the SSE spec allows after the colon.
      dataLines.push(line.slice('data:'.length).replace(/^ /, ''))
    }
    // `: comment`, `retry:`, `id:` and unknown fields are intentionally ignored.
  }
  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}

/**
 * Split a text buffer into complete frames. `\r\n` is normalized so Windows
 * SSE endpoints are tolerated.
 */
export function parseSseStream(input: string): SseParseResult {
  const frames: SseFrame[] = []
  let rest = input.replace(/\r\n/g, '\n')
  let consumed = 0
  for (;;) {
    const blank = rest.indexOf('\n\n', consumed)
    if (blank === -1) break
    const block = rest.slice(consumed, blank)
    // `block + '\n\n'` consumed; the blank line is two chars.
    consumed = blank + 2
    const frame = parseSseBlock(block)
    if (frame) frames.push(frame)
  }
  return { frames, rest: rest.slice(consumed) }
}

/** True when a frame is the canonical `[DONE]` sentinel. */
export function isDoneFrame(frame: SseFrame): boolean {
  return frame.data.trim() === SSE_DONE
}