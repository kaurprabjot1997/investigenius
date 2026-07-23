import { useState } from "react";
import { approveCase, investigateCase } from "../lib/api";
import type { AgentArgument, DemoRole, InvestigationResult } from "../types/investigation";

interface Props {
  caseId: string;
  role: DemoRole;
}

const VERDICT_STYLE: Record<InvestigationResult["verdict"]["verdict"], string> = {
  escalate: "bg-red-100 text-red-800 border-red-300",
  needs_review: "bg-amber-100 text-amber-800 border-amber-300",
  close: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

const CAN_APPROVE: DemoRole[] = ["senior_investigator", "compliance_officer"];

export function InvestigationPanel({ caseId, role }: Props) {
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [narrative, setNarrative] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);

  async function runInvestigation() {
    setLoading(true);
    setError(null);
    setApprovalStatus(null);
    try {
      const res = await investigateCase(caseId, role);
      setResult(res);
      setNarrative(res.verdict.narrative);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Investigation failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(decision: "approve" | "reject") {
    try {
      await approveCase(caseId, decision, narrative, role);
      setApprovalStatus(decision === "approve" ? "Approved and logged to audit trail." : "Rejected and logged to audit trail.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to record decision.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">AI Investigation</h2>
        <button
          onClick={runInvestigation}
          disabled={loading}
          className="px-4 py-2 rounded-md bg-slate-900 text-white text-sm font-medium disabled:opacity-50"
        >
          {loading ? "Running investigation…" : result ? "Re-run investigation" : "Run investigation"}
        </button>
      </div>

      {error && (
        <div className="border border-red-300 bg-red-50 text-red-800 text-sm rounded-md p-3">{error}</div>
      )}

      {result && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <span className={`text-sm font-medium px-3 py-1 rounded-full border ${VERDICT_STYLE[result.verdict.verdict]}`}>
              {result.verdict.verdict.replace("_", " ").toUpperCase()}
            </span>
            <span className="text-sm text-slate-600">
              Confidence: {(result.verdict.confidence * 100).toFixed(0)}%
            </span>
            <span className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
              Source: {result.source === "live" ? "Live model call" : "Replayed (cached) response"}
            </span>
          </div>

          {result.flagged_for_review && (
            <div className="border border-amber-300 bg-amber-50 text-amber-900 text-sm rounded-md p-3">
              Flagged for mandatory human review — {result.uncited_claims.length > 0
                ? `${result.uncited_claims.length} claim(s) referenced a record ID not found in this case's data.`
                : "model confidence fell below the auto-decision threshold."}
              This case cannot be auto-closed or auto-escalated without sign-off below.
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ArgumentCard title="Prosecutor" accent="border-red-200" arg={result.prosecutor} />
            <ArgumentCard title="Defense" accent="border-blue-200" arg={result.defense} />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Draft narrative (editable — for investigator review, not a final determination)
            </label>
            <textarea
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              rows={6}
              className="w-full rounded-md border border-slate-300 p-3 text-sm text-slate-800"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleDecision("approve")}
              disabled={!CAN_APPROVE.includes(role)}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-40"
            >
              Approve
            </button>
            <button
              onClick={() => handleDecision("reject")}
              disabled={!CAN_APPROVE.includes(role)}
              className="px-4 py-2 rounded-md bg-slate-200 text-slate-800 text-sm font-medium disabled:opacity-40"
            >
              Reject
            </button>
            {!CAN_APPROVE.includes(role) && (
              <span className="text-xs text-slate-500">Junior investigators can review but not approve.</span>
            )}
            {approvalStatus && <span className="text-xs text-emerald-700">{approvalStatus}</span>}
          </div>
        </>
      )}
    </div>
  );
}

function ArgumentCard({ title, accent, arg }: { title: string; accent: string; arg: AgentArgument }) {
  return (
    <div className={`rounded-lg border ${accent} p-4 space-y-3 bg-white`}>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="text-sm text-slate-700">{arg.summary}</p>
      <ul className="space-y-2">
        {arg.claims.map((claim, i) => (
          <li key={i} className="text-xs text-slate-600 border-t border-slate-100 pt-2">
            {claim.statement}
            <span className="ml-2 inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-mono">
              {claim.citation_id}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
