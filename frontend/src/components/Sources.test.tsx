import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Sources } from './Sources'
import type { Source } from '../types/chat'

describe('Sources', () => {
  const mockSources: Source[] = [
    {
      document_id: 'doc_1.pdf',
      chunk_id: 'chunk_42',
      snippet: 'This is the relevant passage from document 1.',
      score: 0.9421,
    },
    {
      document_id: 'doc_2.pdf',
      chunk_id: 'chunk_10',
      snippet: 'Another supporting quote.',
    },
  ]

  it('renders sources container and label', () => {
    render(<Sources sources={mockSources} />)

    expect(screen.getByTestId('sources')).toBeInTheDocument()
    expect(screen.getByText('Sources')).toBeInTheDocument()
  })

  it('renders all source chips with doc, chunk, and formatted score', () => {
    render(<Sources sources={mockSources} />)

    expect(screen.getByText('doc_1.pdf')).toBeInTheDocument()
    expect(screen.getByText('chunk_42')).toBeInTheDocument()
    expect(screen.getByText('0.942')).toBeInTheDocument()

    expect(screen.getByText('doc_2.pdf')).toBeInTheDocument()
    expect(screen.getByText('chunk_10')).toBeInTheDocument()
  })

  it('renders snippet as title tooltip attribute', () => {
    render(<Sources sources={mockSources} />)

    const firstChip = screen.getByTitle('This is the relevant passage from document 1.')
    expect(firstChip).toBeInTheDocument()
  })
})
