import { useEffect, useState } from "react";
import { listCases } from "../lib/api";
import type { CaseSummary, DemoRole, Typology } from "../types/investigation";

interface Props {
  role: DemoRole;
  onOpenCase: (caseId: string) => void;
}

const TYPOLOGY_LABEL: Record<Typology, string> = {
  structuring: "Structuring",
  round_tripping: "Round-tripping",
  mule_hub: "Mule hub",
  none: "No pattern",
};

function riskStyle(score: number): string {
  if (score >= 70) return "bg-red-100 text-red-800 border-red-300";
  if (score >= 40) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-slate-100 text-slate-600 border-slate-300";
}

export function CaseQueue({ role, onOpenCase }: Props) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCases(role)
      .then(setCases)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load cases."));
  }, [role]);

  if (error) {
    return <div className="p-6 text-sm text-red-700 border border-red-300 bg-red-50 rounded-md m-6">{error}</div>;
  }
  if (!cases) {
    return <div className="p-6 text-sm text-slate-500">Loading cases…</div>;
  }

  const totalAlerts = cases.reduce((sum, c) => sum + c.alert_count, 0);
  const highRisk = cases.filter((c) => c.risk_score >= 70);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Raw alerts" value={totalAlerts} />
        <StatTile label="Network cases" value={cases.length} sub={`${Math.round((1 - cases.length / Math.max(totalAlerts, 1)) * 100)}% reduction`} />
        <StatTile label="High-risk cases" value={highRisk.length} sub="risk score ≥ 70" accent="text-red-700" />
      </div>

      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Case</th>
              <th className="text-left px-4 py-3 font-medium">Typology</th>
              <th className="text-left px-4 py-3 font-medium">Risk</th>
              <th className="text-left px-4 py-3 font-medium">Accounts</th>
              <th className="text-left px-4 py-3 font-medium">Alerts merged</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr
                key={c.case_id}
                onClick={() => onOpenCase(c.case_id)}
                className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
              >
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{c.case_id}</td>
                <td className="px-4 py-3 text-slate-700">{TYPOLOGY_LABEL[c.typology_guess]}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${riskStyle(c.risk_score)}`}>
                    {c.risk_score.toFixed(0)}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{c.account_count}</td>
                <td className="px-4 py-3 text-slate-600">{c.alert_count}</td>
                <td className="px-4 py-3 text-slate-500 capitalize">{c.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatTile({ label, value, sub, accent }: { label: string; value: number; sub?: string; accent?: string }) {
  return (
    <div className="border border-slate-200 rounded-lg p-4 bg-white">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${accent ?? "text-slate-900"}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </div>
  );
}
