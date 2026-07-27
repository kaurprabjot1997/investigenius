import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { Account, Transaction } from "../types/investigation";

interface Props {
  accounts: Account[];
  transactions: Transaction[];
  /** Smaller, chromeless render for inline previews (e.g. the queue's "how this case was built" panel). */
  compact?: boolean;
}

const TYPE_COLOR: Record<string, string> = {
  business: "#0ea5e9",
  personal: "#64748b",
  external: "#dc2626",
};
const HUB_COLOR = "#d97706";
const DIM_NODE = "rgba(148,163,184,0.35)";
const DIM_LINK = "rgba(203,213,225,0.6)";
const HIGHLIGHT_LINK = "#d97706";

function linkEndId(end: unknown): string {
  return typeof end === "string" ? end : (end as { id: string }).id;
}

export function NetworkGraph({ accounts, transactions, compact = false }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Account | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // react-force-graph-2d auto-measures its container when no explicit width
  // is given — that measurement can come back 0 when the component mounts
  // inside a CSS grid cell nested in a table cell (e.g. the queue's "how
  // this case was built" preview), because the grid/table hasn't finished
  // laying out column widths at the moment the library measures. Measuring
  // the container ourselves with ResizeObserver and passing width
  // explicitly sidesteps that entirely — a rendered-but-invisible 0-width
  // canvas was exactly what produced the blank graph box.
  const [width, setWidth] = useState(compact ? 320 : 640);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const measured = entries[0]?.contentRect.width;
      if (measured && measured > 0) setWidth(measured);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const accountById = useMemo(() => new Map(accounts.map((a) => [a.account_id, a])), [accounts]);

  const { nodes, links, connected, maxAmount } = useMemo(() => {
    const degree: Record<string, number> = {};
    transactions.forEach((t) => {
      degree[t.from_account] = (degree[t.from_account] ?? 0) + 1;
      degree[t.to_account] = (degree[t.to_account] ?? 0) + 1;
    });
    const maxDegree = Math.max(0, ...Object.values(degree));
    // Only crown a hub if someone actually stands out — a 2-account pair
    // shouldn't get a glowing "hub" for having one transaction each.
    const hubId = maxDegree > 2 ? Object.keys(degree).find((id) => degree[id] === maxDegree) : undefined;

    const nodes = accounts.map((a) => ({
      id: a.account_id,
      label: `${a.account_id} — ${a.display_name}`,
      type: a.account_type,
      degree: degree[a.account_id] ?? 0,
      isHub: a.account_id === hubId,
    }));

    const links = transactions.map((t) => ({
      source: t.from_account,
      target: t.to_account,
      txnId: t.txn_id,
      amount: t.amount,
      label: `${t.txn_id}: $${t.amount.toFixed(0)}`,
    }));

    const connected: Record<string, Set<string>> = {};
    links.forEach((l) => {
      (connected[l.source] ??= new Set()).add(l.target);
      (connected[l.target] ??= new Set()).add(l.source);
    });

    return { nodes, links, connected, maxAmount: Math.max(1, ...links.map((l) => l.amount)) };
  }, [accounts, transactions]);

  function dimmed(nodeId: string): boolean {
    if (!hoveredId || nodeId === hoveredId) return false;
    return !connected[hoveredId]?.has(nodeId);
  }

  const height = compact ? 220 : 380;

  return (
    <div className="relative">
      <div ref={containerRef} className="border border-slate-200 rounded-lg overflow-hidden" style={{ height }}>
        {/* eslint-disable @typescript-eslint/no-explicit-any -- react-force-graph-2d's accessor callbacks are typed against its internal node/link shape, not ours */}
        <ForceGraph2D
          graphData={{ nodes, links } as any}
          width={width}
          backgroundColor="#ffffff"
          nodeId="id"
          nodeLabel="label"
          nodeVal={(n: any) => (n.isHub ? 9 : 4 + Math.min(3, n.degree * 0.3))}
          nodeColor={(n: any) => (dimmed(n.id) ? DIM_NODE : n.isHub ? HUB_COLOR : TYPE_COLOR[n.type] ?? "#64748b")}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
            if (node.isHub && !dimmed(node.id)) {
              const pulse = 1 + 0.25 * Math.sin(Date.now() / 300);
              ctx.save();
              ctx.shadowColor = "rgba(217,119,6,0.65)";
              ctx.shadowBlur = 10;
              ctx.beginPath();
              ctx.arc(node.x, node.y, 12 * pulse, 0, 2 * Math.PI);
              ctx.strokeStyle = "rgba(217,119,6,0.6)";
              ctx.lineWidth = 1.75;
              ctx.stroke();
              ctx.restore();
            }
            if (!compact && globalScale > 1.1) {
              ctx.font = `${10 / globalScale}px ui-monospace, monospace`;
              ctx.fillStyle = dimmed(node.id) ? "rgba(100,116,139,0.4)" : "#1e293b";
              ctx.textAlign = "center";
              ctx.fillText(node.id, node.x, node.y + 14 / globalScale);
            }
          }}
          linkColor={(l: any) => {
            if (!hoveredId) return "#cbd5e1";
            return linkEndId(l.source) === hoveredId || linkEndId(l.target) === hoveredId ? HIGHLIGHT_LINK : DIM_LINK;
          }}
          linkLabel="label"
          linkWidth={(l: any) => 0.5 + (l.amount / maxAmount) * 3.5}
          linkDirectionalArrowLength={compact ? 0 : 4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={() => "#94a3b8"}
          linkDirectionalParticles={compact ? 1 : 2}
          linkDirectionalParticleWidth={(l: any) => 1 + (l.amount / maxAmount) * 2}
          linkDirectionalParticleSpeed={0.006}
          linkDirectionalParticleColor={() => "#d97706"}
          onNodeHover={(n: any) => setHoveredId(n ? n.id : null)}
          onNodeClick={compact ? undefined : (n: any) => setSelected(accountById.get(n.id) ?? null)}
          cooldownTicks={100}
          height={height}
        />
      </div>

      {!compact && (
        <div className="flex flex-wrap items-center gap-4 px-3 py-2 border border-t-0 border-slate-200 rounded-b-lg bg-slate-50 text-xs text-slate-500">
          <Legend color={TYPE_COLOR.business} label="Business" />
          <Legend color={TYPE_COLOR.personal} label="Personal" />
          <Legend color={TYPE_COLOR.external} label="External" />
          <Legend color={HUB_COLOR} label="Hub (highest degree)" />
          <span className="ml-auto text-slate-400">Hover to trace connections · click a node for details · particles show fund flow</span>
        </div>
      )}

      {selected && !compact && (
        <div className="absolute top-3 right-3 bg-white border border-slate-200 rounded-lg shadow-xl p-3 w-64 text-xs z-10">
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono font-semibold text-slate-800">{selected.account_id}</span>
            <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-700 leading-none">
              ✕
            </button>
          </div>
          <div className="text-slate-600">
            {selected.display_name} · {selected.account_type}
          </div>
          {selected.kyc_notes && <div className="text-slate-500 mt-1">{selected.kyc_notes}</div>}
          {selected.profile && (
            <div className="mt-2 pt-2 border-t border-slate-100 space-y-0.5 text-slate-600">
              <div>Tenure: {selected.profile.tenure_years}y</div>
              {selected.profile.income_after_tax_range && <div>Income: {selected.profile.income_after_tax_range}</div>}
              <div>Digital: {selected.profile.digital_enrolled ? "Enrolled" : "Not enrolled"}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <i className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
      {label}
    </span>
  );
}
