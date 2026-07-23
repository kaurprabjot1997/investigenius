import { useState } from "react";
import { CaseDetail } from "./pages/CaseDetail";
import { CaseQueue } from "./pages/CaseQueue";
import type { DemoRole } from "./types/investigation";

const ROLES: DemoRole[] = ["junior_investigator", "senior_investigator", "compliance_officer"];

export function App() {
  const [role, setRole] = useState<DemoRole>("senior_investigator");
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white px-6 py-4 flex items-center justify-between">
        <span className="font-semibold text-slate-900">InvestiGenius</span>
        <label className="text-sm text-slate-600">
          Viewing as:{" "}
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as DemoRole)}
            className="ml-2 border border-slate-300 rounded px-2 py-1 text-sm"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </header>

      {openCaseId ? (
        <CaseDetail caseId={openCaseId} role={role} onBack={() => setOpenCaseId(null)} />
      ) : (
        <CaseQueue role={role} onOpenCase={setOpenCaseId} />
      )}
    </div>
  );
}
