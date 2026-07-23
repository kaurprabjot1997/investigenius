import { useEffect, useState } from "react";
import { getAuditTrail } from "../lib/api";
import type { AuditEntry, DemoRole } from "../types/investigation";

interface Props {
  caseId: string;
  role: DemoRole;
}

export function AuditTrail({ caseId, role }: Props) {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAuditTrail(caseId, role)
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load audit trail."));
  }, [caseId, role]);

  if (error) {
    return <div className="text-sm text-red-700 border border-red-300 bg-red-50 rounded-md p-3">{error}</div>;
  }
  if (!entries) {
    return <div className="text-sm text-slate-500">Loading audit trail…</div>;
  }
  if (entries.length === 0) {
    return <div className="text-sm text-slate-500 border border-slate-200 rounded-md p-4 bg-white">No actions recorded for this case yet.</div>;
  }

  return (
    <div className="border border-slate-200 rounded-lg bg-white divide-y divide-slate-100">
      {entries.map((e, i) => (
        <div key={i} className="p-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-slate-800">{e.action.replace("_", " ")}</span>
            <span className="text-xs text-slate-400">{e.timestamp}</span>
          </div>
          <div className="text-xs text-slate-500 mt-1">by {e.actor}</div>
          <pre className="text-xs text-slate-500 mt-2 bg-slate-50 rounded p-2 overflow-x-auto">
            {JSON.stringify(e.payload, null, 2)}
          </pre>
          <div className="text-[10px] text-slate-400 mt-2 font-mono truncate" title={e.row_hash}>
            hash: {e.row_hash}
          </div>
        </div>
      ))}
    </div>
  );
}
