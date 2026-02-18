"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listAuditLogs } from "@/lib/api";

interface AuditEntry {
  id: string;
  tenant_id: string;
  run_id: string | null;
  action: string;
  workflow: string | null;
  step: string | null;
  model_used: string | null;
  prompt_template_id: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number | null;
  input_summary: string | null;
  output_summary: string | null;
  reason_code: string | null;
  actor: string;
  timestamp: string;
}

const actionColor: Record<string, string> = {
  ticket_created: "bg-blue-100 text-blue-700",
  classified: "bg-purple-100 text-purple-700",
  draft_generated: "bg-green-100 text-green-700",
  email_sent: "bg-teal-100 text-teal-700",
  lead_created: "bg-blue-100 text-blue-700",
  lead_extracted: "bg-purple-100 text-purple-700",
  lead_qualified: "bg-green-100 text-green-700",
  crm_updated: "bg-teal-100 text-teal-700",
  error: "bg-red-100 text-red-700",
  budget_exceeded: "bg-orange-100 text-orange-700",
};

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState({ action: "", workflow: "" });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filter.action) params.action = filter.action;
      if (filter.workflow) params.workflow = filter.workflow;
      const data = await listAuditLogs(params);
      setLogs(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, [filter]);

  return (
    <AdminLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Audit Log</h2>
        <div className="flex gap-2">
          <select
            value={filter.workflow}
            onChange={(e) => setFilter({ ...filter, workflow: e.target.value })}
            className="border rounded px-3 py-1 text-sm"
          >
            <option value="">All Workflows</option>
            <option value="support_triage">Support Triage</option>
            <option value="lead_qualify">Lead Qualify</option>
          </select>
          <input
            placeholder="Filter action..."
            value={filter.action}
            onChange={(e) => setFilter({ ...filter, action: e.target.value })}
            className="border rounded px-3 py-1 text-sm w-40"
          />
          <button onClick={load} className="bg-gray-200 px-3 py-1 rounded text-sm">Refresh</button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Time</th>
              <th className="text-left px-4 py-3 font-medium">Action</th>
              <th className="text-left px-4 py-3 font-medium">Workflow</th>
              <th className="text-left px-4 py-3 font-medium">Step</th>
              <th className="text-left px-4 py-3 font-medium">Model</th>
              <th className="text-left px-4 py-3 font-medium">Tokens</th>
              <th className="text-left px-4 py-3 font-medium">Cost</th>
              <th className="text-left px-4 py-3 font-medium">Summary</th>
              <th className="text-left px-4 py-3 font-medium">Actor</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                  {new Date(l.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${actionColor[l.action] || "bg-gray-100"}`}>
                    {l.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs">{l.workflow || "—"}</td>
                <td className="px-4 py-3 text-xs">{l.step || "—"}</td>
                <td className="px-4 py-3 text-xs font-mono">{l.model_used || "—"}</td>
                <td className="px-4 py-3 text-xs">
                  {l.input_tokens || l.output_tokens
                    ? `${l.input_tokens || 0}/${l.output_tokens || 0}`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-xs">
                  {l.estimated_cost_usd ? `$${l.estimated_cost_usd.toFixed(4)}` : "—"}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                  {l.output_summary || l.input_summary || "—"}
                </td>
                <td className="px-4 py-3 text-xs">{l.actor}</td>
              </tr>
            ))}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-400">No audit entries yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </AdminLayout>
  );
}
