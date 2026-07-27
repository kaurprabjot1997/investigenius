import type { DemoRole } from "../types/investigation";

interface Persona {
  role: DemoRole;
  name: string;
  title: string;
  initials: string;
}

// Fictional personas, not real people — gives the RBAC role-switcher a human
// face for the demo ("advisor journey") without pretending this is real
// authentication. See backend/app/api/routes.py's _require_role docstring:
// the role is still enforced server-side, this screen just picks which
// persona's session the browser sends.
const PERSONAS: Persona[] = [
  { role: "junior_investigator", name: "Alex Chen", title: "Junior AML Investigator", initials: "AC" },
  { role: "senior_investigator", name: "Priya Sharma", title: "Senior AML Investigator", initials: "PS" },
  { role: "compliance_officer", name: "Morgan Lee", title: "Compliance Officer", initials: "ML" },
];

interface Props {
  onSignIn: (persona: Persona) => void;
}

export function SignIn({ onSignIn }: Props) {
  return (
    <div className="min-h-screen bg-brand-blue-dark flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="text-white text-3xl font-bold tracking-wide">RBC</div>
          <div className="text-brand-gold text-xs uppercase tracking-[0.2em] mt-1">Technology &amp; Operations</div>
          <h1 className="text-white text-xl font-semibold mt-6">InvestiGenius</h1>
          <p className="text-slate-300 text-sm mt-1">AML Investigation Copilot</p>
        </div>

        <div className="bg-white rounded-lg shadow-xl p-6 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Sign in as</p>
          {PERSONAS.map((p) => (
            <button
              key={p.role}
              onClick={() => onSignIn(p)}
              className="w-full flex items-center gap-3 p-3 rounded-md border border-slate-200 hover:border-brand-blue hover:bg-slate-50 transition-colors text-left"
            >
              <span className="w-9 h-9 rounded-full bg-brand-blue text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">
                {p.initials}
              </span>
              <span>
                <span className="block text-sm font-medium text-slate-900">{p.name}</span>
                <span className="block text-xs text-slate-500">{p.title}</span>
              </span>
            </button>
          ))}
        </div>
        <p className="text-center text-xs text-slate-400 mt-6">
          Demo sign-in, not real authentication — role-based permissions are still enforced server-side regardless of
          which persona you pick.
        </p>
      </div>
    </div>
  );
}

export type { Persona };
export { PERSONAS };
