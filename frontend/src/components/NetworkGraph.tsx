import ForceGraph2D from "react-force-graph-2d";
import type { Account, Transaction } from "../types/investigation";

interface Props {
  accounts: Account[];
  transactions: Transaction[];
  hubAccountIds?: Set<string>;
}

const TYPE_COLOR: Record<string, string> = {
  business: "#0ea5e9",
  personal: "#64748b",
  external: "#dc2626",
};

export function NetworkGraph({ accounts, transactions, hubAccountIds }: Props) {
  const graphData = {
    nodes: accounts.map((a) => ({
      id: a.account_id,
      label: `${a.account_id} — ${a.display_name}`,
      color: hubAccountIds?.has(a.account_id) ? "#b45309" : TYPE_COLOR[a.account_type] ?? "#64748b",
      val: hubAccountIds?.has(a.account_id) ? 8 : 4,
    })),
    links: transactions.map((t) => ({
      source: t.from_account,
      target: t.to_account,
      label: `${t.txn_id}: $${t.amount.toFixed(0)}`,
    })),
  };

  return (
    <div className="border border-slate-200 rounded-lg bg-white overflow-hidden" style={{ height: 360 }}>
      <ForceGraph2D
        graphData={graphData}
        nodeLabel="label"
        nodeColor="color"
        nodeVal="val"
        linkLabel="label"
        linkColor={() => "#cbd5e1"}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        height={360}
        cooldownTicks={80}
      />
    </div>
  );
}
