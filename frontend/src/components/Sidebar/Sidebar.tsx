import type { Conversation } from '../../types/chat'
import { ConversationItem } from './ConversationItem'

export interface SidebarProps {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onRename?: (id: string, title: string) => void | Promise<void>
  onDelete?: (id: string) => void
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Conversations">
      {/* Brand Header */}
      <div className="sidebar__brand">
        <div className="sidebar__logo">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div className="sidebar__brand-text">
          <span className="sidebar__brand-name">RAG Orchestrator</span>
          <span className="sidebar__brand-status">
            <span className="sidebar__status-dot" aria-hidden="true" />
            Active
          </span>
        </div>
      </div>

      <div className="sidebar__header">
        <h1 className="sidebar__title">Conversations</h1>
        <button type="button" className="sidebar__new" onClick={onNew} aria-label="New conversation">
          <span className="sidebar__new-plus" aria-hidden="true">+</span> New
        </button>
      </div>

      <div className="sidebar__scroll">
        {conversations.length === 0 ? (
          <div className="sidebar__empty-wrapper">
            <div className="sidebar__empty-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="sidebar__empty">No conversations yet — start a new one.</p>
          </div>
        ) : (
          <ul className="sidebar__list" role="listbox" aria-label="Conversation list">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === activeId}
                onSelect={onSelect}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </ul>
        )}
      </div>

      {/* Footer Info Widget */}
      <div className="sidebar__footer">
        <div className="sidebar__badge">
          <span className="sidebar__badge-icon">⚡</span>
          <span className="sidebar__badge-text">Hybrid Retrieval • Cross-Encoder</span>
        </div>
      </div>
    </aside>
  )
}