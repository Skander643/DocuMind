import { ChangeEvent, useRef, useState } from "react";

import { deleteDocument, reindexDocument, uploadDocuments } from "../api";
import type { DocumentInfo } from "../types";

export function DocumentList({
  docs,
  busy,
  onRefresh,
  onBusy,
  onError,
}: {
  docs: DocumentInfo[];
  busy: boolean;
  onRefresh: () => Promise<void>;
  onBusy: (value: boolean) => void;
  onError: (message: string | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  async function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = event.target.files ? Array.from(event.target.files) : [];
    event.target.value = "";
    if (!files.length) return;
    onBusy(true);
    onError(null);
    try {
      await uploadDocuments(files);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      onBusy(false);
    }
  }

  async function onDelete(doc: DocumentInfo) {
    const ok = window.confirm(`Remove ${doc.filename} from disk and the index?`);
    if (!ok) return;
    setPendingId(doc.doc_id);
    onError(null);
    try {
      await deleteDocument(doc.doc_id);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setPendingId(null);
    }
  }

  async function onReindex(doc: DocumentInfo) {
    setPendingId(doc.doc_id);
    onError(null);
    try {
      await reindexDocument(doc.doc_id);
      await onRefresh();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Re-index failed");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <section className="doc-panel">
      <div className="doc-panel-head">
        <h2>Documents</h2>
        <button
          type="button"
          className="ghost small"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "Indexing…" : "Upload PDF"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={onUpload}
        />
      </div>
      {docs.length === 0 ? (
        <p className="muted">No PDFs yet. Upload a labor-law PDF or add files under data/raw.</p>
      ) : (
        <ul className="doc-list">
          {docs.map((doc) => (
            <li key={doc.doc_id}>
              <div className="doc-meta">
                <span className="doc-name" title={doc.filename}>
                  {doc.filename}
                </span>
                <span className="muted">
                  {doc.status}
                  {doc.n_chunks ? ` · ${doc.n_chunks} chunks` : ""}
                </span>
              </div>
              <div className="doc-actions">
                <button
                  type="button"
                  className="ghost small"
                  disabled={pendingId === doc.doc_id || doc.status === "missing_file"}
                  onClick={() => onReindex(doc)}
                >
                  Reindex
                </button>
                <button
                  type="button"
                  className="ghost small danger"
                  disabled={pendingId === doc.doc_id}
                  onClick={() => onDelete(doc)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
