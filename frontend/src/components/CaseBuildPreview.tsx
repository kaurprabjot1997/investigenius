import { useEffect, useState } from "react";
import { getCase } from "../lib/api";
import { NetworkGraph } from "./NetworkGraph";
import type { CaseDetail, DemoRole } from "../types/investigation";

interface Props {
  caseId: string;
  role: DemoRole;
}

const SAMPLE_ALERT_LIMIT = 5;

// The literal "how a case gets built" story, inline in the queue: raw alerts
// on the left, the automated clustering step in the middle, the network
// those alerts turned into on the right. Fetches full case detail lazily on
// expand — the queue list itself only carries summary counts, not full
// alert/transaction data, since pulling that for all 102 cases up front
// would be wasteful.
export function CaseBuildPreview({ caseId, role }: Props) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAllAlerts, setShowAllAlerts] = useState(false);

  useEffect(() => {
    setDetail(null);
    setError(null);
    setShowAllAlerts(false);
    getCase(caseId, role)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load preview."));
  }, [caseId, role]);

  if (error) {
    return <div className="text-sm text-red-700 p-4">{error}</div>;
  }
  if (!detail) {
    return <div className="text-sm text-slate-400 p-4 animate-pulse">Loading how this case was built…</div>;
  }

  const visibleAlerts = showAllAlerts ? detail.alerts : detail.alerts.slice(0, SAMPLE_ALERT_LIMIT);
  const remaining = detail.alerts.length - visibleAlerts.length;
  const distinctAccounts = new Set(detail.alerts.map((a) => a.account_id)).size;

  return (
    <div className="p-4 bg-slate-50">
      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1.4fr)] gap-4 items-stretch">
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-2">
            1. Raw alerts ({detail.alerts.length})
          </div>
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {visibleAlerts.map((a) => (
              <div key={a.alert_id} className="text-xs border-l-2 border-amber-300 pl-2 py-0.5">
                <span className="font-mono text-slate-500">{a.alert_id}</span>{" "}
                <span className="text-slate-700">{a.reason}</span>
                <span className="text-slate-400"> — {a.account_id}</span>
              </div>
            ))}
          </div>
          {detail.alerts.length > SAMPLE_ALERT_LIMIT && (
            <button
              onClick={() => setShowAllAlerts((v) => !v)}
              className="text-xs text-brand-blue hover:underline pt-1.5"
            >
              {showAllAlerts ? "Show fewer" : `+ ${remaining} more alert(s)`}
            </button>
          )}
        </div>

        <div className="flex md:flex-col items-center justify-center gap-2 px-2">
          <div className="text-slate-300 text-2xl md:rotate-0 rotate-90 md:rotate-0">→</div>
          <div className="text-center bg-brand-blue/5 border border-brand-blue/20 rounded-lg px-3 py-2 w-full md:w-32">
            <div className="text-[9px] font-bold uppercase tracking-wide text-brand-blue">Automated analysis</div>
            <div className="text-[10px] text-slate-500 mt-0.5 leading-tight">
              Graph clustering groups alerts by shared accounts — no manual cross-referencing
            </div>
          </div>
          <div className="text-slate-300 text-2xl md:rotate-0 rotate-90 md:rotate-0">→</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-3 flex flex-col">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-2">
            2. {caseId}'s network — {detail.accounts.length} accounts from {distinctAccounts} alerted account(s)
          </div>
          <div className="flex-1 min-h-[220px]">
            <NetworkGraph accounts={detail.accounts} transactions={detail.transactions} compact />
          </div>
        </div>
      </div>
    </div>
  );
}
