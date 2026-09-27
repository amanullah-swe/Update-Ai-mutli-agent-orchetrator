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
        Send
      </button>
    </form>
  )
}