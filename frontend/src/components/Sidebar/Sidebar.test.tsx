import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Sidebar } from './Sidebar'
import type { Conversation } from '../../types/chat'

describe('Sidebar', () => {
  const mockConversations: Conversation[] = [
    {
      id: 'chat-1',
      title: 'First Chat',
      created_at: '2026-09-28T10:00:00Z',
      updated_at: '2026-09-28T10:00:00Z',
      messages: [{ id: 'm1', role: 'user', content: 'Hello 1', created_at: '2026-09-28T10:00:00Z' }],
    },
    {
      id: 'chat-2',
      title: 'Second Chat',
      created_at: '2026-09-28T11:00:00Z',
      updated_at: '2026-09-28T11:00:00Z',
      messages: [{ id: 'm2', role: 'user', content: 'Hello 2', created_at: '2026-09-28T11:00:00Z' }],
    },
  ]

  it('renders header, title, and new conversation button', () => {
    render(
      <Sidebar
        conversations={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: /conversations/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument()
  })

  it('triggers onNew when "+ New" button is clicked', async () => {
    const user = userEvent.setup()
    const onNew = vi.fn()
    render(
      <Sidebar
        conversations={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNew={onNew}
      />,
    )

    await user.click(screen.getByRole('button', { name: /new conversation/i }))
    expect(onNew).toHaveBeenCalledTimes(1)
  })

  it('renders empty message when conversations list is empty', () => {
    render(
      <Sidebar
        conversations={[]}
        activeId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )

    expect(screen.getByText('No conversations yet — start a new one.')).toBeInTheDocument()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('renders conversation list when conversations are present', () => {
    render(
      <Sidebar
        conversations={mockConversations}
        activeId="chat-1"
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    )

    expect(screen.getByRole('listbox', { name: /conversation list/i })).toBeInTheDocument()
    expect(screen.getByText('First Chat')).toBeInTheDocument()
    expect(screen.getByText('Second Chat')).toBeInTheDocument()
  })

  it('calls onSelect when a conversation item is clicked', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <Sidebar
        conversations={mockConversations}
        activeId="chat-1"
        onSelect={onSelect}
        onNew={vi.fn()}
      />,
    )

    await user.click(screen.getByText('Second Chat'))
    expect(onSelect).toHaveBeenCalledWith('chat-2')
  })
})
