import type { Message } from '../../types/chat'
import { MarkdownContent } from '../Markdown/MarkdownContent'
import { Sources } from '../Sources'

export interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant'

  return (
    <div
      className={`message message--${message.role}${message.error ? ' message--error' : ''}`}
      data-testid={`message-${message.role}`}
    >
      <div className="message__header">
        <div className="message__avatar" aria-hidden="true">
          {isAssistant ? (
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
            </svg>
          )}
        </div>
        <span className="message__author">
          {isAssistant ? 'RAG Assistant' : 'You'}
        </span>
      </div>

      <div className="message__body">
        {message.error ? (
          <p className="message__error-text">{message.content}</p>
        ) : (
          <>
            <MarkdownContent content={message.content} />
            {isAssistant && message.sources && message.sources.length > 0 && (
              <Sources sources={message.sources} />
            )}
          </>
        )}
      </div>
    </div>
  )
}