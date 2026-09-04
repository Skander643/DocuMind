import { useEffect, useState } from "react";

import { getEvalSummary, getHealth, listDocuments } from "./api";
import { Chat } from "./components/Chat";
import { DocumentList } from "./components/DocumentList";
import { EvalPanel } from "./components/EvalPanel";
import { PdfPreview } from "./components/PdfPreview";
import type { Citation, DocumentInfo, EvalSummary, HealthResponse } from "./types";

const CONVERSATION_ID = crypto.randomUUID();

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [docError, setDocError] = useState<string | null>(null);
  const [docBusy, setDocBusy] = useState(false);
  const [evalSummary, setEvalSummary] = useState<EvalSummary | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Citation | null>(null);

  async function refreshDocs() {
    const next = await listDocuments();
    setDocs(next);
  }

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((err: unknown) => {
        setHealthError(err instanceof Error ? err.message : "API unreachable");
      });
    refreshDocs().catch(() => setDocs([]));
    getEvalSummary()
      .then(setEvalSummary)
      .catch((err: unknown) => {
        setEvalError(err instanceof Error ? err.message : "No eval batch yet");
      });
  }, []);

  return (
    <div className={`layout ${preview ? "with-preview" : ""}`}>
      <aside>
        <h1>DocuMind</h1>
        <p className="tagline">Labor-law RAG · FR / AR / EN</p>
        <p className={`badge ${health ? "ok" : "down"}`}>
          {health ? `${health.app} · phase ${health.phase}` : (healthError ?? "checking API…")}
        </p>
        <DocumentList
          docs={docs}
          busy={docBusy}
          onRefresh={refreshDocs}
          onBusy={setDocBusy}
          onError={setDocError}
        />
        {docError && <p className="error">{docError}</p>}
        <EvalPanel summary={evalSummary} error={evalError} />
      </aside>
      <main>
        <Chat
          conversationId={CONVERSATION_ID}
          selected={preview}
          onSelectCitation={setPreview}
        />
      </main>
      {preview && <PdfPreview citation={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}
