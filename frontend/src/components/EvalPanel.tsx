import type { EvalSummary } from "../types";

function pct(value: number | null): string {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

export function EvalPanel({
  summary,
  error,
}: {
  summary: EvalSummary | null;
  error: string | null;
}) {
  return (
    <section className="eval-panel">
      <h2>RAGAS</h2>
      {summary ? (
        <>
          <p className="muted">
            {summary.n_questions} gold questions
            {summary.created_at ? ` · ${summary.created_at.slice(0, 10)}` : ""}
          </p>
          <ul className="eval-metrics">
            <li>
              <span>Faithfulness</span>
              <strong>{pct(summary.faithfulness)}</strong>
            </li>
            <li>
              <span>Answer relevancy</span>
              <strong>{pct(summary.answer_relevancy)}</strong>
            </li>
            <li>
              <span>Context precision</span>
              <strong>{pct(summary.context_precision)}</strong>
            </li>
            <li>
              <span>Context recall</span>
              <strong>{pct(summary.context_recall)}</strong>
            </li>
            <li>
              <span>Refuse accuracy</span>
              <strong>{pct(summary.refuse_accuracy)}</strong>
            </li>
          </ul>
        </>
      ) : (
        <p className="muted">
          {error ?? "No batch yet. From backend: python -m app.eval"}
        </p>
      )}
    </section>
  );
}
