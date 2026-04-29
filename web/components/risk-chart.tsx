"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function RiskChart({ data }: { data: { score_date: string; composite_score: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <XAxis dataKey="score_date" axisLine={false} tickLine={false} tick={{ fill: "#86868B", fontSize: 12 }} minTickGap={32} />
        <YAxis hide domain={[0, 100]} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#FFFFFF",
            border: "1px solid #F5F5F7",
            borderRadius: 8,
            boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
            fontSize: 13,
          }}
          formatter={(v: number) => [v.toFixed(1), "Composite"]}
          labelFormatter={(l) => l}
        />
        <Line
          type="monotone"
          dataKey="composite_score"
          stroke="rgba(0, 113, 227, 0.8)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
