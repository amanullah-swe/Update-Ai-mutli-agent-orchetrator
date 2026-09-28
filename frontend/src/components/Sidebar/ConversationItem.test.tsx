import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Conversation } from '../../types/chat'
import { ConversationItem } from './ConversationItem'

const NOW = new Date().toISOString()

function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return { id: 'c-1', title: 'Old name', created_at: NOW, updated_at: NOW, messages: [], ...overrides }
}

// Opens the three-dot menu for the item, returning the menu element.
async function openMenu(user: ReturnType<typeof userEvent.setup>, label = 'Old name') {
  await user.click(screen.getByLabelText(`More actions for ${label}`))
  return screen.getByRole('menu', { name: `Actions for ${label}` })
}

describe('ConversationItem', () => {
  it('renders the title and selects on click', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<ConversationItem conversation={makeConversation()} active={false} onSelect={onSelect} />)

    await user.click(screen.getByRole('button', { name: 'Old name' }))

    expect(onSelect).toHaveBeenCalledWith('c-1')
  })

  it('shows "Untitled chat" for a null title', () => {
    render(
      <ConversationItem
        conversation={makeConversation({ title: null })}
        active={false}
        onSelect={vi.fn()}
      />,
    )

    expect(screen.getByText('Untitled chat')).toBeInTheDocument()
  })

  it('kebab opens a menu with Rename and Delete, without selecting the chat', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={onSelect}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    const menu = await openMenu(user)
    expect(menu).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Rename' })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Delete' })).toBeInTheDocument()
    // Opening the menu must never select the chat.
    expect(onSelect).not.toHaveBeenCalled()
  })

  it('closes the menu when an action (Rename) is chosen', async () => {
    const user = userEvent.setup()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={vi.fn()}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))

    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    // The Rename action switched the row into its inline editor.
    expect(screen.getByLabelText('Rename conversation')).toBeInTheDocument()
  })

  it('closes the menu on an outside click', async () => {
    const user = userEvent.setup()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('button', { name: 'Old name' }))

    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('closes the menu on Escape', async () => {
    const user = userEvent.setup()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await openMenu(user)
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('renames via the menu: Rename → edit → Enter saves through onRename', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={onRename}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))

    const input = screen.getByLabelText('Rename conversation')
    expect(input).toHaveValue('Old name')

    await user.clear(input)
    await user.type(input, 'New name')
    await user.keyboard('{Enter}')

    expect(onRename).toHaveBeenCalledWith('c-1', 'New name')
    // Editor closed, back to the (parent-owned) title.
    expect(screen.queryByLabelText('Rename conversation')).not.toBeInTheDocument()
    expect(screen.getByText('Old name')).toBeInTheDocument()
  })

  it('cancels the rename on Escape without calling onRename', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={onRename}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))
    await user.type(screen.getByLabelText('Rename conversation'), 'Changed')
    await user.keyboard('{Escape}')

    expect(onRename).not.toHaveBeenCalled()
    expect(screen.queryByLabelText('Rename conversation')).not.toBeInTheDocument()
  })

  it('cancels the rename when the result would be blank', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onRename={onRename}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('menuitem', { name: 'Rename' }))
    await user.clear(screen.getByLabelText('Rename conversation'))
    await user.keyboard('{Enter}')

    expect(onRename).not.toHaveBeenCalled()
  })

  it('calls onDelete when Delete is chosen from the menu', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    render(
      <ConversationItem
        conversation={makeConversation()}
        active={false}
        onSelect={vi.fn()}
        onDelete={onDelete}
      />,
    )

    await openMenu(user)
    await user.click(screen.getByRole('menuitem', { name: 'Delete' }))

    expect(onDelete).toHaveBeenCalledWith('c-1')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })
})