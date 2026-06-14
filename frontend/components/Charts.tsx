"use client";

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Analysis, inr } from "@/lib/api";

const TIP = {
  contentStyle: {
    background: "#0b1220",
    border: "1px solid rgba(255,255,255,0.15)",
    borderRadius: 12,
    color: "#e2e8f0",
  },
  formatter: (v: number) => inr(v),
};

export function ITCDonut({ a }: { a: Analysis }) {
  const data = [
    { name: "Claimable ITC", value: a.gstr3b.itc_available, color: "#22c55e" },
    { name: "Blocked u/s 17(5)", value: a.itc_summary.itc_blocked_value, color: "#ef4444" },
    { name: "At risk (2A)", value: a.reconciliation.summary.total_itc_at_risk, color: "#f59e0b" },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={3}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} stroke="transparent" />
          ))}
        </Pie>
        <Tooltip {...(TIP as any)} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ReconBars({ a }: { a: Analysis }) {
  const s = a.reconciliation.summary;
  const data = [
    { name: "Matched", value: s.matched, color: "#22c55e" },
    { name: "Mismatched", value: s.mismatched, color: "#f59e0b" },
    { name: "Missing in 2A", value: s.missing_in_2a, color: "#ef4444" },
    { name: "Missing in books", value: s.missing_in_books, color: "#64748b" },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} interval={0} />
        <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <Tooltip
          contentStyle={(TIP as any).contentStyle}
          cursor={{ fill: "rgba(255,255,255,0.05)" }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VendorBars({ a }: { a: Analysis }) {
  const top = [...a.reconciliation.lines]
    .filter((l) => l.book_tax > 0)
    .sort((x, y) => y.book_tax - x.book_tax)
    .slice(0, 6)
    .map((l) => ({
      name: (l.supplier || l.gstin || l.invoice_number || "?").slice(0, 16),
      value: l.book_tax,
      risk: l.itc_at_risk,
    }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={top} layout="vertical" margin={{ left: 20 }}>
        <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={110} tick={{ fill: "#94a3b8", fontSize: 11 }} />
        <Tooltip {...(TIP as any)} />
        <Bar dataKey="value" fill="#3b82f6" radius={[0, 6, 6, 0]} />
        <Bar dataKey="risk" fill="#ef4444" radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
