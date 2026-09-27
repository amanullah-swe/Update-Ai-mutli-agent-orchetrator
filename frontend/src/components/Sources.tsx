import type { Source } from '../types/chat'

export interface SourcesProps {
  sources: Source[]
}

/** Citation list attached to an assistant message (traceable back to doc + chunk). */
export function Sources({ sources }: SourcesProps) {
  return (
    <div className="sources" data-testid="sources">
      <p className="sources__label">Sources</p>
      <ul className="sources__list">
        {sources.map((source) => (
          <li key={`${source.document_id}/${source.chunk_id}`} className="source-chip" title={source.snippet}>
            <span className="source-chip__doc">{source.document_id}</span>
            <span className="source-chip__chunk">{source.chunk_id}</span>
            {typeof source.score === 'number' && (
              <span className="source-chip__score">{source.score.toFixed(3)}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}