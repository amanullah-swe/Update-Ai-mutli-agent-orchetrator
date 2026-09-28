import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog } from './ConfirmDialog'

const baseProps = () => ({
  open: true,
  title: 'Delete conversation?',
  message: 'This chat will be removed.',
  confirmLabel: 'Delete',
  cancelLabel: 'Cancel',
  danger: true,
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
})

describe('ConfirmDialog', () => {
  it('renders nothing while closed', () => {
    render(<ConfirmDialog {...baseProps()} open={false} />)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText('Delete conversation?')).not.toBeInTheDocument()
  })

  it('renders the title and message with both actions', () => {
    render(<ConfirmDialog {...baseProps()} />)

    const dialog = screen.getByRole('dialog', { name: 'Delete conversation?' })
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText('This chat will be removed.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
  })

  it('focuses the safe action (Cancel) on open', () => {
    render(<ConfirmDialog {...baseProps()} />)

    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('calls onConfirm from the confirm action, onCancel from cancel', async () => {
    const user = userEvent.setup()
    const props = baseProps()
    render(<ConfirmDialog {...props} />)

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(props.onCancel).toHaveBeenCalledTimes(1)
    expect(props.onConfirm).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Delete' }))
    expect(props.onConfirm).toHaveBeenCalledTimes(1)
  })

  it('dismisses on Escape via onCancel', async () => {
    const user = userEvent.setup()
    const props = baseProps()
    render(<ConfirmDialog {...props} />)

    await user.keyboard('{Escape}')

    expect(props.onCancel).toHaveBeenCalledTimes(1)
    expect(props.onConfirm).not.toHaveBeenCalled()
  })

  it('dismisses when the press starts on the backdrop, not inside the panel', () => {
    const props = baseProps()
    render(<ConfirmDialog {...props} />)
    const panel = screen.getByRole('dialog')

    // A press inside the panel is the user's own business — nothing closes.
    fireEvent.mouseDown(panel)
    expect(props.onCancel).not.toHaveBeenCalled()

    // A press on the backdrop itself dismisses.
    fireEvent.mouseDown(panel.parentElement as HTMLElement)
    expect(props.onCancel).toHaveBeenCalledTimes(1)
  })
})