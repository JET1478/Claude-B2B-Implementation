"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listRuns } from "@/lib/api";

interface Run {
  id: string;
  tenant_id: string;
  workflow: string;
  status: string;
  error_message: string | null;
  claude_calls: number;
  claude_input_tokens: number;
  claude_output_tokens: number;
  local_model_calls: number;
  estimated_cost_usd: number;
  duration_seconds: number | null;
  current_step: string | null;
  created_at: string;
}

const statusColor: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [filter, setFilter] = useState({ workflow: "", status: "" });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filter.workflow) params.workflow = filter.workflow;
      if (filter.status) params.status = filter.status;
      const data = await listRuns(params);
      setRuns(data);
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
        <h2 className="text-2xl font-bold">Pipeline Runs</h2>
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
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            className="border rounded px-3 py-1 text-sm"
          >
            <option value="">All Status</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
          <button onClick={load} className="bg-gray-200 px-3 py-1 rounded text-sm">Refresh</button>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">ID</th>
                <th className="text-left px-4 py-3 font-medium">Workflow</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Step</th>
                <th className="text-left px-4 py-3 font-medium">Claude Tokens</th>
                <th className="text-left px-4 py-3 font-medium">Local Tokens</th>
                <th className="text-left px-4 py-3 font-medium">Cost</th>
                <th className="text-left px-4 py-3 font-medium">Duration</th>
                <th className="text-left px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{r.id.slice(0, 8)}</td>
                  <td className="px-4 py-3">{r.workflow}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${statusColor[r.status] || "bg-gray-100"}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{r.current_step || "-"}</td>
                  <td className="px-4 py-3 text-xs">
                    {r.claude_input_tokens + r.claude_output_tokens > 0
                      ? `${r.claude_input_tokens + r.claude_output_tokens}`
                      : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs">{r.local_model_calls > 0 ? r.local_model_calls : "-"}</td>
                  <td className="px-4 py-3 text-xs">${r.estimated_cost_usd.toFixed(4)}</td>
                  <td className="px-4 py-3 text-xs">
                    {r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                    No runs yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </AdminLayout>
  );
}
