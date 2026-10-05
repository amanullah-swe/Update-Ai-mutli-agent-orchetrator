import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Composer } from './Composer'

describe('Composer', () => {
  it('renders input and submit button with default placeholder', () => {
    render(<Composer onSend={vi.fn()} />)

    const input = screen.getByLabelText('Message input')
    const button = screen.getByRole('button', { name: /send/i })

    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('placeholder', 'Message the assistant…')
    expect(button).toBeInTheDocument()
    expect(button).toBeDisabled()
  })

  it('updates input value on typing and enables send button', async () => {
    const user = userEvent.setup()
    render(<Composer onSend={vi.fn()} />)

    const input = screen.getByLabelText('Message input')
    const button = screen.getByRole('button', { name: /send/i })

    await user.type(input, 'Hello assistant')
    expect(input).toHaveValue('Hello assistant')
    expect(button).not.toBeDisabled()
  })

  it('submits text and clears input on clicking Send', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)

    const input = screen.getByLabelText('Message input')
    const button = screen.getByRole('button', { name: /send/i })

    await user.type(input, 'Tell me about RAG')
    await user.click(button)

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(onSend).toHaveBeenCalledWith('Tell me about RAG')
    expect(input).toHaveValue('')
    expect(button).toBeDisabled()
  })

  it('submits text on pressing Enter', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)

    const input = screen.getByLabelText('Message input')

    await user.type(input, 'What is chunking?{Enter}')

    expect(onSend).toHaveBeenCalledTimes(1)
    expect(onSend).toHaveBeenCalledWith('What is chunking?')
    expect(input).toHaveValue('')
  })

  it('inserts newline on Shift+Enter without sending', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)

    const input = screen.getByLabelText('Message input')

    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2')

    expect(onSend).not.toHaveBeenCalled()
    expect(input).toHaveValue('Line 1\nLine 2')
  })

  it('does not send whitespace-only text', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<Composer onSend={onSend} />)

    const input = screen.getByLabelText('Message input')
    const button = screen.getByRole('button', { name: /send/i })

    await user.type(input, '    {Enter}')
    expect(onSend).not.toHaveBeenCalled()
    expect(button).toBeDisabled()
  })

  it('disables input and button when disabled prop is true', () => {
    render(<Composer onSend={vi.fn()} disabled />)

    const input = screen.getByLabelText('Message input')
    const button = screen.getByRole('button', { name: /send/i })

    expect(input).toBeDisabled()
    expect(input).toHaveAttribute('placeholder', 'Waiting for the assistant…')
    expect(button).toBeDisabled()
  })
})
