import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatPage } from './ChatPage'
import { listChats, getChat, createChat, renameChat, deleteChat } from '../services/chatApi'
import { MockChatService } from '../services/MockChatService'

vi.mock('../services/chatApi', () => ({
  listChats: vi.fn(),
  getChat: vi.fn(),
  createChat: vi.fn(),
  renameChat: vi.fn(),
  deleteChat: vi.fn(),
}))

vi.mock('../services/chatService', () => ({
  createChatService: () => new MockChatService({ tokenDelayMs: 0 }),
}))

const mockListChats = vi.mocked(listChats)
const mockGetChat = vi.mocked(getChat)
const mockCreateChat = vi.mocked(createChat)
const mockRenameChat = vi.mocked(renameChat)
const mockDeleteChat = vi.mocked(deleteChat)

const NOW = new Date().toISOString()

describe('ChatPage Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListChats.mockResolvedValue([])
    mockGetChat.mockResolvedValue({
      id: 'chat-1',
      title: 'Existing Chat',
      created_at: NOW,
      updated_at: NOW,
      messages: [
        { id: 'm1', role: 'user', content: 'What is RAG?', created_at: NOW },
        { id: 'm2', role: 'assistant', content: 'RAG stands for Retrieval-Augmented Generation.', created_at: NOW },
      ],
    })
    mockCreateChat.mockResolvedValue({
      id: 'chat-new',
      title: null,
      created_at: NOW,
      updated_at: NOW,
    })
    mockRenameChat.mockResolvedValue({
      id: 'chat-new',
      title: 'Hello world',
      created_at: NOW,
      updated_at: NOW,
    })
    mockDeleteChat.mockResolvedValue(undefined)
  })

  it('renders initial empty page with welcome prompt and loads conversation list', async () => {
    mockListChats.mockResolvedValue([
      { id: 'chat-1', title: 'Existing Chat', created_at: NOW, updated_at: NOW, message_count: 2, last_message_at: NOW },
    ])

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Existing Chat')).toBeInTheDocument()
      expect(screen.getByText('Ask anything about your documents.')).toBeInTheDocument()
    })
  })

  it('loads transcript when a conversation is selected', async () => {
    const user = userEvent.setup()
    mockListChats.mockResolvedValue([
      { id: 'chat-1', title: 'Existing Chat', created_at: NOW, updated_at: NOW, message_count: 2, last_message_at: NOW },
    ])

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Existing Chat')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Existing Chat'))

    expect(mockGetChat).toHaveBeenCalledWith('chat-1')
    await waitFor(() => {
      expect(screen.getByText('What is RAG?')).toBeInTheDocument()
      const assistantBubble = screen.getByTestId('message-assistant')
      expect(within(assistantBubble).getByText(/Retrieval-Augmented Generation/)).toBeInTheDocument()
    })
  })

  it('creates new conversation on clicking "+ New"', async () => {
    const user = userEvent.setup()
    mockListChats.mockResolvedValue([])

    render(<ChatPage />)

    const newBtn = screen.getByRole('button', { name: /new conversation/i })
    await user.click(newBtn)

    await waitFor(() => {
      expect(mockCreateChat).toHaveBeenCalledTimes(1)
    })
  })

  it('sends message, auto-creates and renames untitled conversation, and streams answer', async () => {
    const user = userEvent.setup()
    mockListChats.mockResolvedValue([])

    render(<ChatPage />)

    const input = screen.getByLabelText('Message input')
    await user.type(input, 'Tell me about dense retrieval{Enter}')

    await waitFor(() => {
      expect(mockCreateChat).toHaveBeenCalledTimes(1)
    })

    await waitFor(() => {
      expect(mockRenameChat).toHaveBeenCalledWith('chat-new', 'Tell me about dense retrieval')
    })

    await waitFor(() => {
      expect(screen.getByText('Tell me about dense retrieval')).toBeInTheDocument()
      const assistantBubble = screen.getByTestId('message-assistant')
      expect(within(assistantBubble).getByText(/canned, mock answer/i)).toBeInTheDocument()
    })
  })

  it('handles delete flow: opens confirm dialog, cancels, and confirms deletion', async () => {
    const user = userEvent.setup()
    mockListChats.mockResolvedValue([
      { id: 'chat-1', title: 'Chat To Delete', created_at: NOW, updated_at: NOW, message_count: 1, last_message_at: NOW },
    ])

    render(<ChatPage />)

    await waitFor(() => {
      expect(screen.getByText('Chat To Delete')).toBeInTheDocument()
    })

    // Open kebab menu
    const kebab = screen.getByRole('button', { name: /more actions for chat to delete/i })
    await user.click(kebab)

    // Click Delete action
    const deleteMenuItem = screen.getByRole('menuitem', { name: /^delete$/i })
    await user.click(deleteMenuItem)

    // Confirm dialog should appear
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/Delete conversation\?/i)).toBeInTheDocument()

    // Test cancel
    const cancelBtn = screen.getByRole('button', { name: /cancel/i })
    await user.click(cancelBtn)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(mockDeleteChat).not.toHaveBeenCalled()

    // Open again and confirm
    await user.click(kebab)
    await user.click(screen.getByRole('menuitem', { name: /^delete$/i }))
    const confirmDeleteBtn = screen.getByRole('button', { name: /^delete$/i })
    await user.click(confirmDeleteBtn)

    await waitFor(() => {
      expect(mockDeleteChat).toHaveBeenCalledWith('chat-1')
    })
  })

  it('displays error banner if fetching conversations fails', async () => {
    mockListChats.mockRejectedValue(new Error('Network error loading chats'))

    render(<ChatPage />)

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Network error loading chats')
    })
  })
})
