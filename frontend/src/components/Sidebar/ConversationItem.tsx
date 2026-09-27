import type { Conversation } from '../../types/chat'

export interface ConversationItemProps {
  conversation: Conversation
  active: boolean
  onSelect: (id: string) => void
}

export function ConversationItem({ conversation, active, onSelect }: ConversationItemProps) {
  const lastMessage = conversation.messages.at(-1)?.content ?? ''
  return (
    <li className={`conversation-item${active ? ' conversation-item--active' : ''}`} role="option" aria-selected={active}>
      <button
        type="button"
        className="conversation-item__button"
        onClick={() => onSelect(conversation.id)}
        aria-current={active ? 'true' : undefined}
      >
        <span className="conversation-item__title" title={conversation.title}>
          {conversation.title}
        </span>
        <span className="conversation-item__preview">{truncate(lastMessage, 60)}</span>
      </button>
    </li>
  )
}

function truncate(text: string, max: number): string {
  const singleLine = text.replace(/\s+/g, ' ').trim()
  return singleLine.length > max ? `${singleLine.slice(0, max)}…` : singleLine
}