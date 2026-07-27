import { useState, type ReactNode } from "react";
import { AlertsQueue } from "./pages/AlertsQueue";
import { CaseDetail } from "./pages/CaseDetail";
import { CaseQueue } from "./pages/CaseQueue";
import { SignIn, type Persona } from "./pages/SignIn";

type View = "cases" | "alerts";

export function App() {
  const [currentUser, setCurrentUser] = useState<Persona | null>(null);
  const [view, setView] = useState<View>("cases");
  const [openCaseId, setOpenCaseId] = useState<string | null>(null);

  if (!currentUser) {
    return <SignIn onSignIn={setCurrentUser} />;
  }

  function openCase(caseId: string) {
    setOpenCaseId(caseId);
  }

  return (
    <div className="min-h-screen">
      <header className="bg-brand-blue border-b-4 border-brand-gold px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-baseline gap-3">
            <span className="font-semibold text-white tracking-wide">RBC</span>
            <span className="text-slate-200 text-sm">InvestiGenius</span>
          </div>
          {!openCaseId && (
            <nav className="flex items-center gap-1">
              <NavTab active={view === "cases"} onClick={() => setView("cases")}>
                Case Queue
              </NavTab>
              <NavTab active={view === "alerts"} onClick={() => setView("alerts")}>
                Alerts Queue
              </NavTab>
            </nav>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="w-7 h-7 rounded-full bg-brand-gold text-brand-blue-dark flex items-center justify-center text-xs font-semibold">
            {currentUser.initials}
          </span>
          <span className="text-sm text-slate-100">
            {currentUser.name} <span className="text-slate-300">· {currentUser.title}</span>
          </span>
          <button
            onClick={() => {
              setCurrentUser(null);
              setOpenCaseId(null);
            }}
            className="text-xs text-slate-200 hover:text-white underline ml-2"
          >
            Sign out
          </button>
        </div>
      </header>

      {openCaseId ? (
        <CaseDetail caseId={openCaseId} role={currentUser.role} onBack={() => setOpenCaseId(null)} />
      ) : view === "alerts" ? (
        <AlertsQueue role={currentUser.role} onOpenCase={openCase} />
      ) : (
        <CaseQueue role={currentUser.role} onOpenCase={openCase} />
      )}
    </div>
  );
}

function NavTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
        active ? "bg-white/15 text-white font-medium" : "text-slate-300 hover:text-white hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}
