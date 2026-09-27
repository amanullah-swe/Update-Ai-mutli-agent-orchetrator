import type { Conversation } from '../../types/chat'
import { ConversationItem } from './ConversationItem'

export interface SidebarProps {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}

export function Sidebar({ conversations, activeId, onSelect, onNew }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Conversations">
      <div className="sidebar__header">
        <h1 className="sidebar__title">Conversations</h1>
        <button type="button" className="sidebar__new" onClick={onNew} aria-label="New conversation">
          + New
        </button>
      </div>

      {conversations.length === 0 ? (
        <p className="sidebar__empty">No conversations yet — start a new one.</p>
      ) : (
        <ul className="sidebar__list" role="listbox" aria-label="Conversation list">
          {conversations.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              conversation={conversation}
              active={conversation.id === activeId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </aside>
  )
}