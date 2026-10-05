import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Transcript } from './Transcript'
import type { Message } from '../../types/chat'

describe('Transcript', () => {
  it('renders welcoming empty state when there are no messages and not loading', () => {
    render(<Transcript messages={[]} isLoading={false} />)

    expect(screen.getByText('Ask anything about your documents.')).toBeInTheDocument()
    expect(
      screen.getByText('Your RAG-grounded answers and sources will appear here.'),
    ).toBeInTheDocument()
  })

  it('renders loading state when loading is true and messages are empty', () => {
    render(<Transcript messages={[]} isLoading={false} loading />)

    expect(screen.getByText('Loading transcript…')).toBeInTheDocument()
    expect(screen.getByText('Loading transcript…').closest('[aria-busy="true"]')).toBeInTheDocument()
  })

  it('renders list of messages', () => {
    const messages: Message[] = [
      {
        id: '1',
        role: 'user',
        content: 'Hi',
        created_at: '2026-09-28T10:00:00Z',
      },
      {
        id: '2',
        role: 'assistant',
        content: 'Hello there!',
        created_at: '2026-09-28T10:00:01Z',
      },
    ]

    render(<Transcript messages={messages} isLoading={false} />)

    expect(screen.getByTestId('message-user')).toHaveTextContent('Hi')
    expect(screen.getByTestId('message-assistant')).toHaveTextContent('Hello there!')
  })

  it('renders pending typing indicator when isLoading is true', () => {
    const messages: Message[] = [
      {
        id: '1',
        role: 'user',
        content: 'Question?',
        created_at: '2026-09-28T10:00:00Z',
      },
    ]

    render(<Transcript messages={messages} isLoading={true} />)

    const pendingDots = document.querySelector('.message--pending')
    expect(pendingDots).toBeInTheDocument()
    expect(pendingDots).toHaveAttribute('aria-busy', 'true')
  })
})
