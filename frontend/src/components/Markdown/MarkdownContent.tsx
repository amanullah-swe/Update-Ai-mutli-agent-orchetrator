import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export interface MarkdownContentProps {
  content: string
}

/** Render assistant text as GitHub-flavored markdown (tables, strikethrough, task lists). */
export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="markdown" data-testid="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}