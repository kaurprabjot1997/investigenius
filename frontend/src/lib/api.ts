import type {
  AuditEntry,
  CaseDetail,
  CaseSummary,
  ChatAnswer,
  DemoRole,
  InvestigationResult,
  QueuedAlert,
  SuggestedQuestion,
} from "../types/investigation";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

function authedFetch(path: string, role: DemoRole, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), "X-Demo-Role": role },
  });
}

export function listCases(role: DemoRole): Promise<CaseSummary[]> {
  return authedFetch("/cases", role)
    .then((res) => unwrap<{ cases: CaseSummary[] }>(res))
    .then((body) => body.cases);
}

export function getCase(caseId: string, role: DemoRole): Promise<CaseDetail> {
  return authedFetch(`/cases/${caseId}`, role).then((res) => unwrap(res));
}

export function listAlerts(role: DemoRole): Promise<QueuedAlert[]> {
  return authedFetch("/alerts", role)
    .then((res) => unwrap<{ alerts: QueuedAlert[] }>(res))
    .then((body) => body.alerts);
}

export function investigateCase(caseId: string, role: DemoRole): Promise<InvestigationResult> {
  return authedFetch(`/cases/${caseId}/investigate`, role, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  }).then((res) => unwrap(res));
}

export function approveCase(
  caseId: string,
  decision: "approve" | "reject",
  note: string,
  role: DemoRole,
): Promise<{ status: string }> {
  return authedFetch(`/cases/${caseId}/approve`, role, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, note }),
  }).then((res) => unwrap(res));
}

export function getAuditTrail(caseId: string, role: DemoRole): Promise<AuditEntry[]> {
  return authedFetch(`/cases/${caseId}/audit`, role)
    .then((res) => unwrap<{ case_id: string; trail: AuditEntry[] }>(res))
    .then((body) => body.trail);
}

export function getSuggestedQuestions(caseId: string, role: DemoRole): Promise<SuggestedQuestion[]> {
  return authedFetch(`/cases/${caseId}/chat/suggested-questions`, role)
    .then((res) => unwrap<{ questions: SuggestedQuestion[] }>(res))
    .then((body) => body.questions);
}

export function askPrecedentChat(
  caseId: string,
  role: DemoRole,
  params: { question?: string; questionId?: string },
): Promise<ChatAnswer> {
  return authedFetch(`/cases/${caseId}/chat`, role, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: params.question ?? "", question_id: params.questionId ?? null }),
  }).then((res) => unwrap(res));
}
