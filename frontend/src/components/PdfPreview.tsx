import { documentFileUrl } from "../api";
import type { Citation } from "../types";

export function PdfPreview({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  const src = citation.doc_id
    ? documentFileUrl(citation.doc_id, citation.page)
    : "";

  return (
    <aside className="pdf-preview" aria-label="Source PDF">
      <header className="pdf-preview-bar">
        <div>
          <strong>{citation.filename}</strong>
          <span className="muted"> p. {citation.page}</span>
        </div>
        <div className="pdf-preview-actions">
          {src && (
            <a href={src} target="_blank" rel="noreferrer">
              Open tab
            </a>
          )}
          <button type="button" className="ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </header>
      {src ? (
        <iframe
          key={`${citation.doc_id}-${citation.page}`}
          title={`${citation.filename} page ${citation.page}`}
          src={src}
        />
      ) : (
        <p className="muted">This citation has no document id, so the PDF cannot be opened.</p>
      )}
    </aside>
  );
}
