import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

export interface ComposerProps {
  onSend: (text: string) => void
  disabled?: boolean
}

/** Bottom input: auto-grows, Enter sends, Shift+Enter inserts a newline. */
export function Composer({ onSend, disabled = false }: ComposerProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Reset height when clearing after a send.
  useEffect(() => {
    const el = textareaRef.current
    if (el && text === '') {
      el.style.height = 'auto'
    }
  }, [text])

  const submit = () => {
    const trimmed = text.trim()
    if (trimmed === '' || disabled) return
    onSend(trimmed)
    setText('')
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  const onInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <div className="composer__container">
        <div className="composer__row">
          <textarea
            ref={textareaRef}
            className="composer__input"
            value={text}
            rows={1}
            placeholder={disabled ? 'Waiting for the assistant…' : 'Message the assistant…'}
            aria-label="Message input"
            disabled={disabled}
            onChange={(event) => setText(event.target.value)}
            onInput={onInput}
            onKeyDown={onKeyDown}
          />
          <button type="submit" className="composer__send" disabled={disabled || text.trim() === ''}>
            <svg
              className="composer__send-icon"
              viewBox="0 0 20 20"
              width="16"
              height="16"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
            Send
          </button>
        </div>
        <div className="composer__footer" aria-hidden="true">
          <span className="composer__hint">
            <strong>Enter</strong> to send • <strong>Shift + Enter</strong> for newline
          </span>
          <span className="composer__badge">Hybrid RAG</span>
        </div>
      </div>
    </form>
  )
}