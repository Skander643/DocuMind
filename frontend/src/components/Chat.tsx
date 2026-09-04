import { FormEvent, useState } from "react";

import { sendChat } from "../api";
import type { ChatMessage, Citation } from "../types";
import { CitationCard } from "./CitationCard";

const PLACEHOLDER = "Ask about Tunisian labor law. Example: Quelle est la durée du congé annuel payé ?";

export function Chat({
  conversationId,
  selected,
  onSelectCitation,
}: {
  conversationId: string;
  selected: Citation | null;
  onSelectCitation: (citation: Citation) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const query = draft.trim();
    if (!query || busy) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    setDraft("");
    setBusy(true);
    setError(null);

    try {
      const result = await sendChat({ query, conversation_id: conversationId });
      const assistant: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        confidence: result.confidence,
        latency_ms: result.latency_ms,
      };
      setMessages((prev) => [...prev, assistant]);
      const first = result.citations[0];
      if (result.confidence === "high" && first) {
        onSelectCitation(first);
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Chat failed";
      setError(detail);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat">
      <div className="transcript">
        {messages.length === 0 && (
          <p className="muted">
            Ask a question. Answers cite PDF pages — click an excerpt to open that page.
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`bubble ${msg.role}`}>
            <p dir="auto">{msg.content}</p>
            {msg.confidence === "low" && (
              <p className="low-confidence">Low confidence — answer not grounded enough.</p>
            )}
            {msg.role === "assistant" && msg.latency_ms != null && (
              <p className="muted latency">{msg.latency_ms} ms</p>
            )}
            {msg.citations && msg.citations.length > 0 && (
              <div className="citations">
                {msg.citations.map((citation) => (
                  <CitationCard
                    key={`${citation.doc_id}-${citation.filename}-${citation.page}-${citation.score}`}
                    citation={citation}
                    active={
                      selected?.doc_id === citation.doc_id &&
                      selected.page === citation.page &&
                      selected.excerpt === citation.excerpt
                    }
                    onOpen={onSelectCitation}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <p className="muted">Retrieving and generating… first answer can take a while.</p>}
      </div>
      {error && <p className="error">{error}</p>}
      <form onSubmit={onSubmit} className="composer">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={PLACEHOLDER}
          rows={3}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !draft.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </form>
    </section>
  );
}
