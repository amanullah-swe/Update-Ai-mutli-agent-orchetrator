import { useEffect, useRef, useState } from 'react'
import type { Conversation } from '../../types/chat'

export interface ConversationItemProps {
  conversation: Conversation
  active: boolean
  onSelect: (id: string) => void
  /** Inline-edit save (Enter/blur). Blank cancels; the title never renames to empty. */
  onRename?: (id: string, title: string) => void | Promise<void>
  /** The user asked to delete this chat; confirmation happens above this item. */
  onDelete?: (id: string) => void
}

/** Roughly the menu's rendered height — used to decide whether it fits below. */
const MENU_FIT_HEIGHT = 96

/**
 * One sidebar conversation. The row selects the chat; a three-dot button opens a
 * small menu with Rename (inline editor: Enter/blur save, Escape cancel) and
 * Delete (which asks the parent to confirm — this component never deletes).
 *
 * The menu closes on choosing an action, on Escape, and on any click outside it,
 * and flips upward when the row sits too close to the viewport bottom to fit it
 * below (the sidebar clips its own overflow).
 */
export function ConversationItem({
  conversation,
  active,
  onSelect,
  onRename,
  onDelete,
}: ConversationItemProps) {
  const [editing, setEditing] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuUp, setMenuUp] = useState(false)
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const kebabRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const firstMenuItemRef = useRef<HTMLButtonElement>(null)
  // Guards the Escape→blur race: cancelling unmounts the editor, which may
  // fire the form's onBlur and re-commit a stale draft.
  const cancelPending = useRef(false)

  const lastMessage = conversation.messages.at(-1)?.content ?? ''
  const label = conversation.title ?? 'Untitled chat'

  // Focus + select the title text when the editor opens.
  useEffect(() => {
    if (editing) {
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing])

  // Menu: focus the first action on open; dismiss on Escape or an outside click.
  useEffect(() => {
    if (!menuOpen) return
    firstMenuItemRef.current?.focus()

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node
      if (menuRef.current?.contains(target) || kebabRef.current?.contains(target)) return
      setMenuOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        kebabRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen])

  const toggleMenu = () => {
    if (menuOpen) {
      setMenuOpen(false)
      return
    }
    const rect = kebabRef.current?.getBoundingClientRect()
    if (rect) setMenuUp(rect.bottom + MENU_FIT_HEIGHT > window.innerHeight)
    setMenuOpen(true)
  }

  const startRename = () => {
    setMenuOpen(false)
    cancelPending.current = false
    setDraft(conversation.title ?? '')
    setEditing(true)
  }

  const commitRename = () => {
    if (cancelPending.current) {
      cancelPending.current = false
      return
    }
    setEditing(false)
    const trimmed = draft.trim()
    if (trimmed && trimmed !== (conversation.title ?? '')) {
      void onRename?.(conversation.id, trimmed)
    }
  }

  const cancelRename = () => {
    cancelPending.current = true
    setEditing(false)
    setDraft(conversation.title ?? '')
  }

  const requestDelete = () => {
    setMenuOpen(false)
    onDelete?.(conversation.id)
  }

  return (
    <li
      className={`conversation-item${active ? ' conversation-item--active' : ''}${
        menuOpen ? ' conversation-item--menu-open' : ''
      }`}
      role="option"
      aria-selected={active}
    >
      {editing ? (
        <form
          className="conversation-item__rename"
          onSubmit={(event) => {
            event.preventDefault()
            commitRename()
          }}
          onBlur={commitRename}
        >
          <input
            ref={inputRef}
            className="conversation-item__rename-input"
            value={draft}
            aria-label="Rename conversation"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                commitRename()
              } else if (event.key === 'Escape') {
                cancelRename()
              }
            }}
          />
        </form>
      ) : (
        <div className="conversation-item__row">
          <button
            type="button"
            className="conversation-item__button"
            onClick={() => onSelect(conversation.id)}
            aria-current={active ? 'true' : undefined}
          >
            <span className="conversation-item__title" title={conversation.title ?? undefined}>
              {label}
            </span>
            <span className="conversation-item__preview">{truncate(lastMessage, 60)}</span>
          </button>
          <button
            ref={kebabRef}
            type="button"
            className="conversation-item__kebab"
            aria-label={`More actions for ${label}`}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={toggleMenu}
          >
            <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
              <circle cx="8" cy="3" r="1.4" fill="currentColor" />
              <circle cx="8" cy="8" r="1.4" fill="currentColor" />
              <circle cx="8" cy="13" r="1.4" fill="currentColor" />
            </svg>
          </button>
          {menuOpen && (
            <div
              ref={menuRef}
              className={`conversation-item__menu${menuUp ? ' conversation-item__menu--up' : ''}`}
              role="menu"
              aria-label={`Actions for ${label}`}
            >
              <button
                ref={firstMenuItemRef}
                type="button"
                role="menuitem"
                className="conversation-item__menu-item"
                onClick={startRename}
              >
                Rename
              </button>
              <button
                type="button"
                role="menuitem"
                className="conversation-item__menu-item conversation-item__menu-item--danger"
                onClick={requestDelete}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      )}
    </li>
  )
}

function truncate(text: string, max: number): string {
  const singleLine = text.replace(/\s+/g, ' ').trim()
  return singleLine.length > max ? `${singleLine.slice(0, max)}…` : singleLine
}
