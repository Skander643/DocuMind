export type Confidence = "high" | "low";

export interface Citation {
  filename: string;
  page: number;
  excerpt: string;
  score: number;
  doc_id: string;
}

export interface ChatRequest {
  query: string;
  conversation_id?: string | null;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  confidence: Confidence;
  latency_ms: number;
  conversation_id?: string | null;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  n_chunks: number;
  language: string | null;
  status: string;
}

export interface EvalSummary {
  created_at: string | null;
  n_questions: number;
  faithfulness: number | null;
  answer_relevancy: number | null;
  context_precision: number | null;
  context_recall: number | null;
  refuse_accuracy: number | null;
}

export interface HealthResponse {
  status: string;
  phase: string;
  app: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: Confidence;
  latency_ms?: number;
}
