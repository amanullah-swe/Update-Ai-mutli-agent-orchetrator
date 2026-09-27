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
  )
}