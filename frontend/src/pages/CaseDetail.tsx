import { useEffect, useState } from "react";
import { AccountProfiles } from "../components/AccountProfiles";
import { AutomatedSignals } from "../components/AutomatedSignals";
import { InvestigationPanel } from "../components/InvestigationPanel";
import { InvestigationPlaybook } from "../components/InvestigationPlaybook";
import { NetworkGraph } from "../components/NetworkGraph";
import { PrecedentChat } from "../components/PrecedentChat";
import { AuditTrail } from "../components/AuditTrail";
import { getCase } from "../lib/api";
import type { CaseDetail as CaseDetailType, DemoRole } from "../types/investigation";

interface Props {
  caseId: string;
  role: DemoRole;
  onBack: () => void;
}

export function CaseDetail({ caseId, role, onBack }: Props) {
  const [detail, setDetail] = useState<CaseDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAudit, setShowAudit] = useState(false);

  useEffect(() => {
    setDetail(null);
    getCase(caseId, role)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load case."));
  }, [caseId, role]);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <button onClick={onBack} className="text-sm text-slate-500 hover:text-slate-800">
        ← Back to case queue
      </button>

      {error && <div className="text-sm text-red-700 border border-red-300 bg-red-50 rounded-md p-3">{error}</div>}

      {!detail && !error && <div className="text-sm text-slate-500">Loading case…</div>}

      {detail && (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-slate-900">{detail.case_id}</h1>
              <p className="text-sm text-slate-500 capitalize">
                {detail.typology_guess.replace("_", " ")} · risk {detail.risk_score.toFixed(0)}/100 · {detail.accounts.length} accounts ·{" "}
                {detail.alerts.length} alerts merged
              </p>
            </div>
            <button onClick={() => setShowAudit((v) => !v)} className="text-sm text-slate-500 hover:text-slate-800 underline">
              {showAudit ? "Hide audit trail" : "View audit trail"}
            </button>
          </div>

          {showAudit ? (
            <AuditTrail caseId={detail.case_id} role={role} />
          ) : (
            <>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 -mb-2">
                Automatic Data Analysis — replaces manual cross-referencing of transaction data and customer profiles
              </div>

              <NetworkGraph accounts={detail.accounts} transactions={detail.transactions} />

              <AccountProfiles accounts={detail.accounts} />

              <AutomatedSignals signals={detail.behavioral_signals} />

              <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Txn</th>
                      <th className="text-left px-3 py-2 font-medium">From</th>
                      <th className="text-left px-3 py-2 font-medium">To</th>
                      <th className="text-left px-3 py-2 font-medium">Amount</th>
                      <th className="text-left px-3 py-2 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.transactions.map((t) => (
                      <tr key={t.txn_id} className="border-t border-slate-100">
                        <td className="px-3 py-2 font-mono text-slate-700">{t.txn_id}</td>
                        <td className="px-3 py-2 font-mono text-slate-600">{t.from_account}</td>
                        <td className="px-3 py-2 font-mono text-slate-600">{t.to_account}</td>
                        <td className="px-3 py-2 text-slate-700">${t.amount.toFixed(2)}</td>
                        <td className="px-3 py-2 text-slate-500">{t.ts}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="border-t border-slate-200 pt-6 space-y-6">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Standardization of Investigation Quality — every case checked against the same published criteria and the same adversarial review process
                </div>

                <InvestigationPlaybook playbook={detail.playbook} />

                <InvestigationPanel caseId={detail.case_id} role={role} />

                <PrecedentChat caseId={detail.case_id} role={role} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
