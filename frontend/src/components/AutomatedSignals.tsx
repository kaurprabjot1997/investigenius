import type { BehavioralSignal } from "../types/investigation";

interface Props {
  signals: BehavioralSignal[];
}

// The other half of "automatic data analysis": beyond clustering which
// accounts form a network, this surfaces transactional red flags computed
// from client-profile data (income band, tenure) vs. actual transaction
// volume — backend/app/graph/signals.py. Built only on financial-capacity
// fields, never demographic/segmentation ones (see that module's governance
// note) — and shown here, separate from the graph risk score, not blended
// into it.
export function AutomatedSignals({ signals }: Props) {
  if (signals.length === 0) {
    return (
      <div className="border border-slate-200 rounded-lg bg-white px-4 py-3">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">Automated Data Analysis</span>
        <p className="text-sm text-slate-500 mt-2">No behavioral anomalies detected against client profile data for this case.</p>
      </div>
    );
  }

  return (
    <div className="border border-amber-200 rounded-lg overflow-hidden bg-white">
      <div className="px-4 py-3 bg-amber-50 border-b border-amber-100">
        <span className="text-xs font-semibold uppercase tracking-wide text-amber-800">
          Automated Data Analysis — {signals.length} signal{signals.length > 1 ? "s" : ""} found
        </span>
      </div>
      <div className="divide-y divide-slate-100">
        {signals.map((s, i) => (
          <div key={i} className="px-4 py-3">
            <div className="text-sm text-slate-800">
              <span className="font-mono text-xs text-slate-500 mr-2">{s.account_id}</span>
              {s.label}
            </div>
            <div className="text-xs text-slate-500 mt-1">{s.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
