import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageBubble } from './MessageBubble'
import type { Message } from '../../types/chat'

describe('MessageBubble', () => {
  it('renders user message correctly', () => {
    const userMessage: Message = {
      id: 'm-user',
      role: 'user',
      content: 'What is semantic search?',
      created_at: '2026-09-28T10:00:00Z',
    }

    render(<MessageBubble message={userMessage} />)

    const bubble = screen.getByTestId('message-user')
    expect(bubble).toBeInTheDocument()
    expect(bubble).toHaveClass('message--user')
    expect(bubble).toHaveTextContent('What is semantic search?')
  })

  it('renders assistant message with markdown content', () => {
    const assistantMessage: Message = {
      id: 'm-assistant',
      role: 'assistant',
      content: 'Semantic search uses **embeddings** to match intent.',
      created_at: '2026-09-28T10:00:01Z',
    }

    render(<MessageBubble message={assistantMessage} />)

    const bubble = screen.getByTestId('message-assistant')
    expect(bubble).toBeInTheDocument()
    expect(bubble).toHaveClass('message--assistant')
    expect(screen.getByText('embeddings').tagName.toLowerCase()).toBe('strong')
  })

  it('renders sources when assistant message has sources', () => {
    const assistantMessageWithSources: Message = {
      id: 'm-assistant-sources',
      role: 'assistant',
      content: 'Here is the answer.',
      created_at: '2026-09-28T10:00:01Z',
      sources: [
        {
          document_id: 'rag_guide.pdf',
          chunk_id: 'c1',
          snippet: 'Guide snippet',
          score: 0.95,
        },
      ],
    }

    render(<MessageBubble message={assistantMessageWithSources} />)

    expect(screen.getByTestId('sources')).toBeInTheDocument()
    expect(screen.getByText('rag_guide.pdf')).toBeInTheDocument()
  })

  it('does not render sources for user messages even if sources array is provided', () => {
    const userMessageWithSources: Message = {
      id: 'm-user-sources',
      role: 'user',
      content: 'User query with sources',
      created_at: '2026-09-28T10:00:00Z',
      sources: [
        {
          document_id: 'doc.pdf',
          chunk_id: 'c1',
          snippet: 'Snippet',
        },
      ],
    }

    render(<MessageBubble message={userMessageWithSources} />)

    expect(screen.queryByTestId('sources')).not.toBeInTheDocument()
  })

  it('renders error state with error class and message text', () => {
    const errorMessage: Message = {
      id: 'm-error',
      role: 'assistant',
      content: 'Failed to connect to backend stream.',
      error: true,
      created_at: '2026-09-28T10:00:02Z',
    }

    render(<MessageBubble message={errorMessage} />)

    const bubble = screen.getByTestId('message-assistant')
    expect(bubble).toHaveClass('message--error')
    expect(screen.getByText('Failed to connect to backend stream.')).toHaveClass('message__error-text')
    expect(screen.queryByTestId('markdown-content')).not.toBeInTheDocument()
  })
})
