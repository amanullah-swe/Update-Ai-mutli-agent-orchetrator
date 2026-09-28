import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

export interface ConfirmDialogProps {
  open: boolean
  title: string
  message?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Marks the confirm action as destructive (red). */
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Controlled confirmation modal — the in-app replacement for `window.confirm`.
 *
 * Rendered into `document.body` through a portal, so no ancestor's overflow or
 * stacking context can clip it. Escape and a backdrop click dismiss it, and the
 * safe action (cancel) takes focus on open. Nothing is confirmed implicitly:
 * the caller owns the decision and only acts in `onConfirm`.
 */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)
  // Keep the latest cancel handler without re-running the keydown effect (which
  // would steal focus back to Cancel on every parent render).
  const onCancelRef = useRef(onCancel)
  useEffect(() => {
    onCancelRef.current = onCancel
  }, [onCancel])

  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancelRef.current()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  if (!open) return null

  return createPortal(
    <div
      className="modal"
      onMouseDown={(event) => {
        // Only a press that starts on the backdrop itself dismisses.
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <div className="modal__panel" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <h2 className="modal__title" id={titleId}>
          {title}
        </h2>
        {message !== undefined && <p className="modal__message">{message}</p>}
        <div className="modal__actions">
          <button ref={cancelRef} type="button" className="modal__button" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`modal__button modal__button--primary${danger ? ' modal__button--danger' : ''}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
