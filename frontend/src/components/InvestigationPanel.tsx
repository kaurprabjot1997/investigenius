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

type Stage = "idle" | "prosecutor" | "defense" | "adjudicator" | "done";
const STAGE_ORDER: Stage[] = ["prosecutor", "defense", "adjudicator", "done"];
const STAGE_LABEL: Record<Exclude<Stage, "idle">, string> = {
  prosecutor: "Prosecutor building the case for suspicion",
  defense: "Defense searching for legitimate explanations",
  adjudicator: "Adjudicator weighing both arguments",
  done: "Investigation complete",
};

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function InvestigationPanel({ caseId, role }: Props) {
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [narrative, setNarrative] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<string | null>(null);

  async function runInvestigation() {
    setLoading(true);
    setError(null);
    setApprovalStatus(null);
    setResult(null);
    setStage("prosecutor");
    try {
      const res = await investigateCase(caseId, role);
      // The response already contains everything — the agents genuinely do
      // run in this order server-side (Prosecutor+Defense in parallel, then
      // Adjudicator), so staging the reveal to match rather than dumping
      // the whole result at once is honest, not just decorative.
      await delay(500);
      setStage("defense");
      await delay(500);
      setStage("adjudicator");
      await delay(600);
      setResult(res);
      setNarrative(res.verdict.narrative);
      setStage("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Investigation failed.");
      setStage("idle");
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

  const stageProgress = stage === "idle" ? -1 : STAGE_ORDER.indexOf(stage);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wide bg-slate-700 text-white px-1.5 py-0.5 rounded">
              This case's evidence only
            </span>
            <h2 className="text-sm font-semibold text-slate-900 uppercase tracking-wide">AI Investigation</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">Prosecutor/Defense argue for and against suspicion using only this case's own accounts and transactions.</p>
        </div>
        <button
          onClick={runInvestigation}
          disabled={loading}
          className="px-4 py-2 rounded-md bg-brand-blue text-white text-sm font-medium disabled:opacity-50 hover:bg-brand-blue-dark transition-colors"
        >
          {loading ? "Running investigation…" : result ? "Re-run investigation" : "Run investigation"}
        </button>
      </div>

      {loading && (
        <div className="border border-slate-200 bg-slate-50 rounded-md p-4 space-y-2">
          {(["prosecutor", "defense", "adjudicator"] as const).map((s, i) => {
            const isPast = stageProgress > i;
            const isCurrent = stageProgress === i;
            return (
              <div key={s} className="flex items-center gap-2 text-sm">
                <span
                  className={`w-4 h-4 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] transition-colors ${
                    isPast ? "bg-emerald-500 text-white" : isCurrent ? "bg-brand-blue text-white animate-pulse" : "bg-slate-200 text-slate-400"
                  }`}
                >
                  {isPast ? "✓" : ""}
                </span>
                <span className={isPast || isCurrent ? "text-slate-800" : "text-slate-400"}>{STAGE_LABEL[s]}</span>
              </div>
            );
          })}
        </div>
      )}

      {error && (
        <div className="border border-red-300 bg-red-50 text-red-800 text-sm rounded-md p-3">{error}</div>
      )}

      {result && (
        <div className="space-y-6 animate-[fadeIn_0.3s_ease-in]">
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
              className="w-full rounded-md border border-slate-300 p-3 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => handleDecision("approve")}
              disabled={!CAN_APPROVE.includes(role)}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-40 hover:bg-emerald-700 transition-colors"
            >
              Approve
            </button>
            <button
              onClick={() => handleDecision("reject")}
              disabled={!CAN_APPROVE.includes(role)}
              className="px-4 py-2 rounded-md bg-slate-200 text-slate-800 text-sm font-medium disabled:opacity-40 hover:bg-slate-300 transition-colors"
            >
              Reject
            </button>
            {!CAN_APPROVE.includes(role) && (
              <span className="text-xs text-slate-500">Junior investigators can review but not approve.</span>
            )}
            {approvalStatus && <span className="text-xs text-emerald-700">{approvalStatus}</span>}
          </div>
        </div>
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
