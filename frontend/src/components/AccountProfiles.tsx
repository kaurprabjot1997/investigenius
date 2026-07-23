import type { Account } from "../types/investigation";

interface Props {
  accounts: Account[];
}

// Segmentation/demographic fields render here for investigator context only.
// They are never read by the backend's automated risk scoring (app/graph/
// clustering.py) — see data/profiles.py's governance note. Shown as context
// because real AML investigators do use this kind of profile information
// when weighing a case, not because it drives the graph-based risk score.
export function AccountProfiles({ accounts }: Props) {
  const withProfile = accounts.filter((a) => a.profile);

  if (withProfile.length === 0) {
    return null;
  }

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div className="px-3 py-2 bg-slate-50 text-xs text-slate-500 border-b border-slate-100">
        Client profile context (mock UCP-style data — shown to investigators, excluded from automated risk scoring)
      </div>
      <table className="w-full text-xs">
        <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
          <tr>
            <th className="text-left px-3 py-2 font-medium">Account</th>
            <th className="text-left px-3 py-2 font-medium">Tenure</th>
            <th className="text-left px-3 py-2 font-medium">Income</th>
            <th className="text-left px-3 py-2 font-medium">Occupation</th>
            <th className="text-left px-3 py-2 font-medium">Residence</th>
            <th className="text-left px-3 py-2 font-medium">Digital</th>
            <th className="text-left px-3 py-2 font-medium">Products</th>
          </tr>
        </thead>
        <tbody>
          {withProfile.map((a) => {
            const p = a.profile!;
            return (
              <tr key={a.account_id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono text-slate-700">{a.account_id}</td>
                <td className="px-3 py-2 text-slate-600">
                  {p.tenure_years}y{p.new_to_canada_segment ? " · new to Canada" : ""}
                </td>
                <td className="px-3 py-2 text-slate-600">{p.income_after_tax_range || "—"}</td>
                <td className="px-3 py-2 text-slate-600">{p.occupation || "—"}</td>
                <td className="px-3 py-2 text-slate-600">
                  {p.residence_country}
                  {p.non_resident_tax_flag ? " (non-resident)" : ""}
                </td>
                <td className="px-3 py-2 text-slate-600">{p.digital_enrolled ? "Enrolled" : "Not enrolled"}</td>
                <td className="px-3 py-2 text-slate-600">{p.active_product_count}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
