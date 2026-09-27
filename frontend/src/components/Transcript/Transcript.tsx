import { useEffect, useRef } from 'react'
import type { Message } from '../../types/chat'
import { MessageBubble } from './MessageBubble'

export interface TranscriptProps {
  messages: Message[]
  isLoading: boolean
}

export function Transcript({ messages, isLoading }: TranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, isLoading])

  return (
    <div className="transcript" ref={scrollRef} aria-label="Messages">
      {messages.length === 0 ? (
        <div className="transcript__empty">
          <p>Ask anything about your documents.</p>
          <p className="transcript__hint">Your RAG-grounded answers and sources will appear here.</p>
        </div>
      ) : (
        <div className="transcript__list">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isLoading && (
            <div aria-busy="true" className="message message--assistant message--pending">
              <span className="typing-dots" aria-hidden="true">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}