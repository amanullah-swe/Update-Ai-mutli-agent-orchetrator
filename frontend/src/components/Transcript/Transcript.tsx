import { useEffect, useRef } from 'react'
import type { Message } from '../../types/chat'
import { MessageBubble } from './MessageBubble'

export interface TranscriptProps {
  messages: Message[]
  isLoading: boolean
  /** Fetching the transcript from the server (GET /api/chats/{id}). */
  loading?: boolean
}

export function Transcript({ messages, isLoading, loading = false }: TranscriptProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, isLoading, loading])

  return (
    <div className="transcript" ref={scrollRef} aria-label="Messages">
      {loading && messages.length === 0 ? (
        <div className="transcript__empty" aria-busy="true">
          <div className="transcript__loading-spinner" aria-hidden="true" />
          <p>Loading transcript…</p>
        </div>
      ) : messages.length === 0 ? (
        <div className="transcript__empty">
          <div className="transcript__hero-badge">
            <span className="transcript__hero-spark" aria-hidden="true">✨</span>
            <span>RAG Knowledge Engine</span>
          </div>

          <p className="transcript__welcome-title">Ask anything about your documents.</p>
          <p className="transcript__hint">Your RAG-grounded answers and sources will appear here.</p>

          <div className="transcript__cards" aria-hidden="true">
            <div className="transcript__card">
              <span className="transcript__card-icon">⚡</span>
              <span className="transcript__card-title">Hybrid Retrieval</span>
              <span className="transcript__card-desc">Dense semantic embeddings combined with sparse BM25 keyword matching</span>
            </div>
            <div className="transcript__card">
              <span className="transcript__card-icon">🎯</span>
              <span className="transcript__card-title">Cross-Encoder Rerank</span>
              <span className="transcript__card-desc">High-precision reranking model scoring relevance before generation</span>
            </div>
            <div className="transcript__card">
              <span className="transcript__card-icon">📑</span>
              <span className="transcript__card-title">Direct Citations</span>
              <span className="transcript__card-desc">Every response anchored with verifiable document and chunk citations</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="transcript__list">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isLoading && (
            <div aria-busy="true" className="message message--assistant message--pending">
              <div className="message__avatar" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 18a8 8 0 110-16 8 8 0 010 16z" opacity="0.3"/>
                  <path d="M12 6a6 6 0 100 12 6 6 0 000-12zm-2 5a1 1 0 112 0 1 1 0 01-2 0zm4 0a1 1 0 112 0 1 1 0 01-2 0z"/>
                </svg>
              </div>
              <span className="typing-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}