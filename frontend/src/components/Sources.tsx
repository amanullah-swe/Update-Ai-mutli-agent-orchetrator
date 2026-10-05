import type { Source } from '../types/chat'

export interface SourcesProps {
  sources: Source[]
}

/** Citation list attached to an assistant message (traceable back to doc + chunk). */
export function Sources({ sources }: SourcesProps) {
  return (
    <div className="sources" data-testid="sources">
      <div className="sources__header">
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="sources__icon"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="sources__label">Sources</p>
        <span className="sources__count" aria-hidden="true">({sources.length})</span>
      </div>
      <ul className="sources__list">
        {sources.map((source) => (
          <li key={`${source.document_id}/${source.chunk_id}`} className="source-chip" title={source.snippet}>
            <span className="source-chip__doc-icon" aria-hidden="true">📄</span>
            <span className="source-chip__doc">{source.document_id}</span>
            <span className="source-chip__chunk">{source.chunk_id}</span>
            {typeof source.score === 'number' && (
              <span className="source-chip__score">
                <span className="source-chip__score-val">{source.score.toFixed(3)}</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}