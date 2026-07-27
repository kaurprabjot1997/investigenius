import { Fragment, useEffect, useMemo, useState } from "react";
import { CaseBuildPreview } from "../components/CaseBuildPreview";
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

type SortKey = "risk_score" | "case_id" | "typology_guess" | "account_count" | "alert_count";
type SortDir = "asc" | "desc";

function riskStyle(score: number): string {
  if (score >= 70) return "bg-red-100 text-red-800 border-red-300";
  if (score >= 40) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-slate-100 text-slate-600 border-slate-300";
}

export function CaseQueue({ role, onOpenCase }: Props) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [typologyFilter, setTypologyFilter] = useState<Typology | "all">("all");
  const [search, setSearch] = useState("");
  const [highRiskOnly, setHighRiskOnly] = useState(false);
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

  useEffect(() => {
    listCases(role)
      .then(setCases)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load cases."));
  }, [role]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const filteredSorted = useMemo(() => {
    if (!cases) return [];
    let rows = cases;
    if (typologyFilter !== "all") rows = rows.filter((c) => c.typology_guess === typologyFilter);
    if (highRiskOnly) rows = rows.filter((c) => c.risk_score >= 70);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((c) => c.case_id.toLowerCase().includes(q));
    }
    const sorted = [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [cases, typologyFilter, highRiskOnly, search, sortKey, sortDir]);

  if (error) {
    return <div className="p-6 text-sm text-red-700 border border-red-300 bg-red-50 rounded-md m-6">{error}</div>;
  }
  if (!cases) {
    return (
      <div className="max-w-5xl mx-auto p-6 space-y-6 animate-pulse">
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-slate-100 border border-slate-200" />
          ))}
        </div>
        <div className="h-64 rounded-lg bg-slate-100 border border-slate-200" />
      </div>
    );
  }

  const totalAlerts = cases.reduce((sum, c) => sum + c.alert_count, 0);
  const highRisk = cases.filter((c) => c.risk_score >= 70);

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Raw alerts" value={totalAlerts} />
        <StatTile label="Network cases" value={cases.length} sub={`${Math.round((1 - cases.length / Math.max(totalAlerts, 1)) * 100)}% reduction`} />
        <StatTile
          label="High-risk cases"
          value={highRisk.length}
          sub={highRiskOnly ? "showing only these — click to clear" : "risk score ≥ 70 — click to filter"}
          accent="text-red-700"
          onClick={() => setHighRiskOnly((v) => !v)}
          active={highRiskOnly}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search case ID…"
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue"
        />
        <select
          value={typologyFilter}
          onChange={(e) => setTypologyFilter(e.target.value as Typology | "all")}
          className="border border-slate-300 rounded-md px-2 py-1.5 text-sm"
        >
          <option value="all">All typologies</option>
          {(Object.keys(TYPOLOGY_LABEL) as Typology[]).map((t) => (
            <option key={t} value={t}>
              {TYPOLOGY_LABEL[t]}
            </option>
          ))}
        </select>
        {(search || typologyFilter !== "all" || highRiskOnly) && (
          <button
            onClick={() => {
              setSearch("");
              setTypologyFilter("all");
              setHighRiskOnly(false);
            }}
            className="text-xs text-slate-500 hover:text-slate-800 underline"
          >
            Clear filters
          </button>
        )}
        <span className="text-xs text-slate-400 ml-auto">
          {filteredSorted.length} of {cases.length} cases
        </span>
      </div>

      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <SortableHeader label="Case" sortKey="case_id" active={sortKey} dir={sortDir} onClick={toggleSort} />
              <SortableHeader label="Typology" sortKey="typology_guess" active={sortKey} dir={sortDir} onClick={toggleSort} />
              <SortableHeader label="Risk" sortKey="risk_score" active={sortKey} dir={sortDir} onClick={toggleSort} />
              <SortableHeader label="Accounts" sortKey="account_count" active={sortKey} dir={sortDir} onClick={toggleSort} />
              <SortableHeader label="Alerts merged" sortKey="alert_count" active={sortKey} dir={sortDir} onClick={toggleSort} />
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Built from</th>
            </tr>
          </thead>
          <tbody>
            {filteredSorted.map((c) => {
              const isExpanded = expandedCaseId === c.case_id;
              return (
                <Fragment key={c.case_id}>
                  <tr
                    onClick={() => onOpenCase(c.case_id)}
                    className="border-t border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
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
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedCaseId(isExpanded ? null : c.case_id);
                        }}
                        className="text-xs text-brand-blue hover:underline whitespace-nowrap"
                      >
                        {isExpanded ? "Hide ▲" : "See how ▾"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="border-t border-slate-100">
                      <td colSpan={7} className="p-0">
                        <CaseBuildPreview caseId={c.case_id} role={role} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {filteredSorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-slate-400">
                  No cases match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SortableHeader({
  label,
  sortKey,
  active,
  dir,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  active: SortKey;
  dir: SortDir;
  onClick: (key: SortKey) => void;
}) {
  const isActive = active === sortKey;
  return (
    <th
      onClick={() => onClick(sortKey)}
      className="text-left px-4 py-3 font-medium cursor-pointer select-none hover:text-slate-800"
    >
      {label}
      <span className={`ml-1 inline-block transition-transform ${isActive ? "opacity-100" : "opacity-0"} ${isActive && dir === "asc" ? "rotate-180" : ""}`}>
        ▾
      </span>
    </th>
  );
}

function StatTile({
  label,
  value,
  sub,
  accent,
  onClick,
  active,
}: {
  label: string;
  value: number;
  sub?: string;
  accent?: string;
  onClick?: () => void;
  active?: boolean;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      onClick={onClick}
      className={`border rounded-lg p-4 bg-white text-left transition-colors ${
        active ? "border-red-300 ring-2 ring-red-100" : "border-slate-200"
      } ${onClick ? "hover:border-slate-300 cursor-pointer" : ""}`}
    >
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${accent ?? "text-slate-900"}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-1">{sub}</div>}
    </Tag>
  );
}
