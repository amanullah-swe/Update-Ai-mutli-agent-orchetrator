import { describe, expect, it } from 'vitest'
import { isDoneFrame, parseSseBlock, parseSseStream } from './sse'

describe('parseSseBlock', () => {
  it('parses event + data', () => {
    expect(parseSseBlock('event: token\ndata: hello')).toEqual({ event: 'token', data: 'hello' })
  })

  it('defaults event to "message"', () => {
    expect(parseSseBlock('data: hi')).toEqual({ event: 'message', data: 'hi' })
  })

  it('strips the single leading space after the colon', () => {
    expect(parseSseBlock('data: {json}')).toEqual({ event: 'message', data: '{json}' })
  })

  it('ignores comment lines and unknown fields', () => {
    expect(parseSseBlock(': keepalive\nretry: 10\ndata: ok')).toEqual({
      event: 'message',
      data: 'ok',
    })
  })

  it('returns null when there is no data', () => {
    expect(parseSseBlock('event: heartbeat')).toBeNull()
  })
})

describe('parseSseStream', () => {
  it('parses consecutive frames separated by blank lines', () => {
    const input = 'event: token\ndata: a\n\nevent: done\ndata: [DONE]\n\n'
    const { frames, rest } = parseSseStream(input)
    expect(frames).toHaveLength(2)
    expect(frames[0]).toEqual({ event: 'token', data: 'a' })
    expect(frames[1]).toEqual({ event: 'done', data: '[DONE]' })
    expect(rest).toBe('')
  })

  it('keeps an incomplete trailing frame in rest', () => {
    const { frames, rest } = parseSseStream('event: token\ndata: partial')
    expect(frames).toHaveLength(0)
    expect(rest).toBe('event: token\ndata: partial')
  })

  it('continues a partial frame across chunks', () => {
    const first = parseSseStream('event: token\ndata: hel')
    expect(first.frames).toHaveLength(0)

    const second = parseSseStream(`${first.rest}lo\n\n`)
    expect(second.frames).toHaveLength(1)
    expect(second.frames[0]).toEqual({ event: 'token', data: 'hello' })
  })

  it('normalizes CRLF line endings', () => {
    const { frames } = parseSseStream('event: token\r\ndata: hi\r\n\r\n')
    expect(frames).toHaveLength(1)
    expect(frames[0].data).toBe('hi')
  })

  it('joins multi-line data with newlines', () => {
    const { frames } = parseSseStream('data: one\ndata: two\n\n')
    expect(frames[0].data).toBe('one\ntwo')
  })

  it('returns empty frames for an empty input', () => {
    expect(parseSseStream('')).toEqual({ frames: [], rest: '' })
  })
})

describe('isDoneFrame', () => {
  it('recognizes the [DONE] sentinel', () => {
    expect(isDoneFrame({ event: 'message', data: '[DONE]' })).toBe(true)
    expect(isDoneFrame({ event: 'token', data: 'hello' })).toBe(false)
  })
})