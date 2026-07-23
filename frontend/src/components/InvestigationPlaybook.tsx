import type { PlaybookItem } from "../types/investigation";

interface Props {
  playbook: PlaybookItem[];
}

// The literal, visible answer to "standardization of investigation quality":
// every case of a given typology is checked against the same published
// criteria by the same deterministic code (backend/data/playbooks.py) —
// not an implicit, case-by-case judgment call.
export function InvestigationPlaybook({ playbook }: Props) {
  if (playbook.length === 0) {
    return null;
  }
  const matchedCount = playbook.filter((p) => p.matched).length;

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-600">
          Standardized Investigation Playbook
        </span>
        <span className="text-xs text-slate-500">
          {matchedCount}/{playbook.length} criteria matched
        </span>
      </div>
      <div className="divide-y divide-slate-100">
        {playbook.map((item) => (
          <div key={item.id} className="px-4 py-3 flex gap-3 items-start">
            <span
              className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold ${
                item.matched ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400"
              }`}
            >
              {item.matched ? "✓" : "–"}
            </span>
            <div>
              <div className="text-sm text-slate-800">
                <span className="font-mono text-xs text-slate-500 mr-2">{item.id}</span>
                {item.criterion}
              </div>
              <div className="text-xs text-slate-500 mt-1">{item.evidence}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
