import { useEffect, useMemo, useState } from "react";
import { listAlerts } from "../lib/api";
import type { DemoRole, QueuedAlert, Typology } from "../types/investigation";

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

function riskStyle(score: number | null): string {
  if (score === null) return "bg-slate-100 text-slate-500 border-slate-200";
  if (score >= 70) return "bg-red-100 text-red-800 border-red-300";
  if (score >= 40) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-slate-100 text-slate-600 border-slate-300";
}

// The raw input to the whole pipeline — every alert exactly as it looked
// before graph clustering ever touched it. This is the "high volume of
// alerts" the case brief names, made literal: a real AML triage team's
// actual inbox, before any automated analysis groups it into cases.
export function AlertsQueue({ role, onOpenCase }: Props) {
  const [alerts, setAlerts] = useState<QueuedAlert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [reasonFilter, setReasonFilter] = useState<string>("all");

  useEffect(() => {
    listAlerts(role)
      .then(setAlerts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load alerts."));
  }, [role]);

  const reasonOptions = useMemo(() => {
    if (!alerts) return [];
    return Array.from(new Set(alerts.map((a) => a.reason))).sort();
  }, [alerts]);

  const filtered = useMemo(() => {
    if (!alerts) return [];
    let rows = alerts;
    if (reasonFilter !== "all") rows = rows.filter((a) => a.reason === reasonFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (a) => a.alert_id.toLowerCase().includes(q) || a.account_id.toLowerCase().includes(q) || a.reason.toLowerCase().includes(q),
      );
    }
    return rows;
  }, [alerts, search, reasonFilter]);

  if (error) {
    return <div className="p-6 text-sm text-red-700 border border-red-300 bg-red-50 rounded-md m-6">{error}</div>;
  }
  if (!alerts) {
    return <div className="max-w-5xl mx-auto p-6 text-sm text-slate-500 animate-pulse">Loading alerts queue…</div>;
  }

  const distinctReasons = reasonOptions.length;
  const distinctCases = new Set(alerts.map((a) => a.case_id).filter(Boolean)).size;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Raw alerts in queue" value={alerts.length} />
        <StatTile label="Distinct alert types" value={distinctReasons} sub="different monitoring rules firing" />
        <StatTile label="Merged into" value={distinctCases} sub="network cases via automated clustering" accent="text-brand-blue" />
      </div>

      <div className="border border-amber-200 bg-amber-50 rounded-lg p-3 text-xs text-amber-900">
        This is the team's actual inbox before any automated analysis — every alert a transaction-monitoring rule fired,
        one row each. Click any row to see the network case it was automatically clustered into.
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search alert ID, account, reason…"
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
        />
        <select
          value={reasonFilter}
          onChange={(e) => setReasonFilter(e.target.value)}
          className="border border-slate-300 rounded-md px-2 py-1.5 text-sm max-w-xs"
        >
          <option value="all">All alert types ({reasonOptions.length})</option>
          {reasonOptions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {(search || reasonFilter !== "all") && (
          <button
            onClick={() => {
              setSearch("");
              setReasonFilter("all");
            }}
            className="text-xs text-slate-500 hover:text-slate-800 underline"
          >
            Clear filters
          </button>
        )}
        <span className="text-xs text-slate-400 ml-auto">
          {filtered.length} of {alerts.length} alerts
        </span>
      </div>

      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Alert</th>
              <th className="text-left px-4 py-3 font-medium">Account</th>
              <th className="text-left px-4 py-3 font-medium">Reason</th>
              <th className="text-left px-4 py-3 font-medium">Raised</th>
              <th className="text-left px-4 py-3 font-medium">Clustered into</th>
              <th className="text-left px-4 py-3 font-medium">Case risk</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 250).map((a) => (
              <tr
                key={a.alert_id}
                onClick={() => a.case_id && onOpenCase(a.case_id)}
                className={`border-t border-slate-100 transition-colors ${a.case_id ? "hover:bg-slate-50 cursor-pointer" : ""}`}
              >
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{a.alert_id}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{a.account_id}</td>
                <td className="px-4 py-3 text-slate-700">{a.reason}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{a.raised_at}</td>
                <td className="px-4 py-3 font-mono text-xs text-brand-blue">{a.case_id ?? "—"}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${riskStyle(a.risk_score)}`}>
                    {a.risk_score !== null ? a.risk_score.toFixed(0) : "—"}
                    {a.typology_guess && a.typology_guess !== "none" ? ` · ${TYPOLOGY_LABEL[a.typology_guess]}` : ""}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-400">
                  No alerts match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {filtered.length > 250 && (
          <div className="px-4 py-2 text-xs text-slate-400 border-t border-slate-100 bg-slate-50">
            Showing first 250 of {filtered.length} — narrow with search or the alert-type filter to see more.
          </div>
        )}
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
