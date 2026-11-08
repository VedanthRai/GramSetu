// Typed API client. No secrets live in the browser: all provider keys stay on the server.

export type LangCode = "hi-IN" | "kn-IN" | "ta-IN" | "en-IN";

export interface Language {
  code: LangCode;
  english: string;
  native: string;
  voices: string[];
  default_voice: string;
}

export interface Choice { value: string; label: string }
export interface SummaryLine { field: string; label: string; value: string; source_type: string }

export interface Message {
  id: string;
  role: "assistant" | "user";
  text: string;
  kind: string;
  lang: LangCode;
  at: string;
  field?: string;
  choices?: Choice[] | null;
  summary?: SummaryLine[];
  sources?: string[];
  source_url?: string;
  secure_input?: { target: string };
  secure_typing?: boolean;
  completed_steps?: string[];
  raw_transcript?: string;
  portal?: string;
  consequence?: string;
}

export interface ExtractedField {
  field_name: string;
  normalized_value: string;
  original_user_expression: string;
  source_type: string;
  sensitivity_level: string;
}

export interface TaskIntent {
  task_id: string;
  intent: string;
  portal_id: string | null;
  user_language: string;
  required_fields: string[];
  known_fields: Record<string, ExtractedField>;
  missing_fields: string[];
  clarification_question: string | null;
  source_references: string[];
  completion_criteria: string;
}

export interface PlanStep {
  action_id: string;
  action_type: string;
  target: string;
  expected_result: string;
  requires_authorization: boolean;
  explanation: string;
  status: string;
  error_message: string | null;
}

export interface SummaryCard {
  title: string;
  reference: string | null;
  lines: SummaryLine[];
  message: string;
  language: LangCode;
  demo_notice: string;
  created_at: string;
}

export interface SessionSnapshot {
  id: string;
  language: LangCode;
  state: string;
  messages: Message[];
  task: TaskIntent | null;
  summary: SummaryLine[];
  expected_field: string | null;
  result: { reference: string | null; description: string } | null;
  summary_card: SummaryCard | null;
  plan: PlanStep[];
  screenshots: string[];
  reasoning: { label: string; is_ai: boolean; model: string | null };
  last_turn: { server_ms?: number; reasoning_ms?: number; intent?: string };
}

export interface TimelineEvent {
  id: number;
  at: string;
  actor: string;
  kind: string;
  description: string;
  data: Record<string, unknown>;
}

export interface ProviderHealth {
  name: string;
  kind: string;
  configured: boolean;
  reachable: boolean | null;
  last_latency_ms: number | null;
  last_error: string | null;
  model?: string;
  mode?: string;
  label?: string;
  is_ai?: boolean;
  provider?: string;
  fixture_mode?: boolean;
}

export interface ProvidersStatus {
  stt: ProviderHealth;
  tts: ProviderHealth;
  reasoning: ProviderHealth;
  browser: { name: string; headless: boolean; last_error: string | null };
}

export interface UsageRow { day: string; kind: string; calls: number; audio_seconds: number; chars: number; cache_hits: number; errors: number }
export interface Usage {
  label: string;
  official_balance_available: boolean;
  official_balance_note: string;
  today: string;
  today_calls: number;
  daily_limit: number;
  fixture_mode: boolean;
  rows: UsageRow[];
}

export interface TranscribeResult {
  transcript: string;
  literal: string | null;
  language: LangCode;
  latency_ms: number;
  model: string;
  audio_seconds: number;
  source: string;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function parse<T>(r: Response): Promise<T> {
  if (r.ok) return (await r.json()) as T;
  let code = `HTTP_${r.status}`;
  let message = r.statusText || "Request failed";
  try {
    const body = (await r.json()) as { detail?: unknown };
    const d = body.detail;
    if (typeof d === "string") message = d;
    else if (d && typeof d === "object" && "message" in d) {
      const o = d as { code?: string; message?: string };
      message = o.message ?? message;
      code = o.code ?? code;
    }
  } catch {
    /* non-JSON error body */
  }
  throw new ApiError(r.status, code, message);
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  languages: () => fetch("/api/languages").then((r) => parse<{ verified: Language[]; pending: { code: string; english: string }[]; code_mixed: { status: string; note: string } }>(r)),
  providers: () => fetch("/api/providers/status").then((r) => parse<ProvidersStatus>(r)),
  usage: () => fetch("/api/usage").then((r) => parse<Usage>(r)),
  createSession: (language: LangCode, retain_history: boolean) =>
    fetch("/api/sessions", json({ language, retain_history })).then((r) => parse<{ session: SessionSnapshot }>(r)),
  getSession: (id: string) => fetch(`/api/sessions/${id}`).then((r) => parse<{ session: SessionSnapshot }>(r)),
  turn: (id: string, text: string, raw_transcript?: string, choice?: { field: string; value: string }) =>
    fetch(`/api/sessions/${id}/turns`, json({ text, raw_transcript, choice })).then((r) =>
      parse<{ session: SessionSnapshot; turn: SessionSnapshot["last_turn"] }>(r)),
  review: (id: string) => fetch(`/api/sessions/${id}/review`, { method: "POST" }).then((r) => parse<{ session: SessionSnapshot }>(r)),
  approve: (id: string, kind: "start" | "final") =>
    fetch(`/api/sessions/${id}/approve`, json({ kind })).then((r) => parse<{ session: SessionSnapshot }>(r)),
  cancel: (id: string) => fetch(`/api/sessions/${id}/cancel`, { method: "POST" }).then((r) => parse<{ session: SessionSnapshot }>(r)),
  userInput: (id: string, value: string) =>
    fetch(`/api/sessions/${id}/user-input`, json({ value })).then((r) => parse<{ session: SessionSnapshot }>(r)),
  resume: (id: string) => fetch(`/api/sessions/${id}/resume`, { method: "POST" }).then((r) => parse<{ session: SessionSnapshot }>(r)),
  demoSms: (id: string) => fetch(`/api/sessions/${id}/demo-sms`).then((r) => parse<{ message: { to: string; code: string; text: string } | null; notice: string }>(r)),
  events: (id: string) => fetch(`/api/sessions/${id}/events`).then((r) => parse<{ events: TimelineEvent[] }>(r)),
  deleteSession: (id: string) => fetch(`/api/sessions/${id}`, { method: "DELETE" }).then((r) => parse<{ deleted: boolean }>(r)),
  history: () => fetch("/api/history").then((r) => parse<{ tasks: { id: string; session_id: string; intent: string; portal_id: string; created_at: string; status: string; language: string | null; data: { reference?: string } }[] }>(r)),
  sources: () => fetch("/api/sources").then((r) => parse<SourcesDoc>(r)),
  portals: () => fetch("/api/portals").then((r) => parse<{ portals: PortalInfo[] }>(r)),
  evalResults: () => fetch("/api/eval/results").then((r) => parse<EvalResults>(r)),
  fixtures: () => fetch("/api/fixtures/audio").then((r) => parse<{ fixtures: AudioFixture[] }>(r)),
  transcribe: async (wav: Blob, language: LangCode, sessionId?: string): Promise<TranscribeResult> => {
    const fd = new FormData();
    fd.append("audio_file", wav, "speech.wav");
    fd.append("language", language);
    if (sessionId) fd.append("session_id", sessionId);
    return parse<TranscribeResult>(await fetch("/api/speech/transcribe", { method: "POST", body: fd }));
  },
};

export interface AudioFixture { name: string; language: LangCode; label: string; synthetic: boolean; transcript_reference: string }

export interface SourceStatement { id: string; kind: string; text: string }
export interface SchemeSource {
  scheme_id: string;
  official_name: string;
  official_source_url: string;
  source_title: string;
  jurisdiction: string;
  retrieved_at: string;
  last_verified_at: string;
  status: string;
  statements: SourceStatement[];
  required_documents: { status: string; note: string };
  verification_notes: string;
}
export interface SourcesDoc { retrieval_note: string; schemes: SchemeSource[] }

export interface PortalInfo {
  portal_id: string;
  name: string;
  route_prefix: string;
  supported_tasks: string[];
  enabled: boolean;
  read_only: boolean;
  fields: string[];
  permitted_actions: string[];
  consequential_targets: string[];
  secret_targets: string[];
  completion_evidence: string;
}

export interface EvalMetric { name: string; value: number | null; numerator?: number; denominator?: number; unit?: string; note?: string }
export interface EvalResults {
  status?: string;
  run_at?: string;
  reasoning_provider?: string;
  dataset_size?: number;
  metrics?: EvalMetric[];
  stt?: { sample_size: number; wer: number | null; cer: number | null; mean_latency_ms: number | null; failures: number; note: string; items: { id: string; lang: string; reference: string; hypothesis: string; cer: number | null; audio?: string; latency_ms?: number; script_mismatch?: boolean }[]; scored?: number; script_mismatch?: number };
  items?: { id: string; lang: string; text: string; expected_intent: string; got_intent: string; intent_ok: boolean; fields_ok: number; fields_total: number }[];
  pending?: string[];
}
