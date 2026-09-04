import type { Citation } from "../types";

export function CitationCard({
  citation,
  active,
  onOpen,
}: {
  citation: Citation;
  active: boolean;
  onOpen: (citation: Citation) => void;
}) {
  return (
    <button
      type="button"
      className={`citation ${active ? "active" : ""}`}
      onClick={() => onOpen(citation)}
      aria-pressed={active}
      title={`Open ${citation.filename} page ${citation.page}`}
    >
      <header>
        <span className="citation-file">{citation.filename}</span>
        <span className="citation-page">p. {citation.page}</span>
        <span className="citation-score">{citation.score.toFixed(2)}</span>
      </header>
      <p>{citation.excerpt}</p>
    </button>
  );
}
