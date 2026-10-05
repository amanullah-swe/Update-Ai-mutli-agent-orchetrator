import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarkdownContent } from './MarkdownContent'

describe('MarkdownContent', () => {
  it('renders plain text content', () => {
    render(<MarkdownContent content="Hello world" />)
    expect(screen.getByTestId('markdown-content')).toHaveTextContent('Hello world')
  })

  it('renders bold and italic formatting', () => {
    render(<MarkdownContent content="This is **bold** and *italic* text" />)
    const boldEl = screen.getByText('bold')
    const italicEl = screen.getByText('italic')

    expect(boldEl.tagName.toLowerCase()).toBe('strong')
    expect(italicEl.tagName.toLowerCase()).toBe('em')
  })

  it('renders markdown lists correctly', () => {
    const listContent = `
- Item 1
- Item 2
- Item 3
`
    render(<MarkdownContent content={listContent} />)
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('Item 1')
  })

  it('renders code blocks and inline code', () => {
    const codeContent = 'Here is `inline code` and:\n\n```python\nprint("hello")\n```'
    render(<MarkdownContent content={codeContent} />)

    const inlineCode = screen.getByText('inline code')
    expect(inlineCode.tagName.toLowerCase()).toBe('code')

    const preBlock = screen.getByText(/print\("hello"\)/)
    expect(preBlock).toBeInTheDocument()
  })

  it('renders GitHub Flavored Markdown tables (remark-gfm)', () => {
    const tableContent = `
| Header 1 | Header 2 |
| -------- | -------- |
| Value 1  | Value 2  |
`
    render(<MarkdownContent content={tableContent} />)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Header 1')).toBeInTheDocument()
    expect(screen.getByText('Value 1')).toBeInTheDocument()
  })
})
