"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listTickets } from "@/lib/api";

interface Ticket {
  id: string;
  tenant_id: string;
  subject: string | null;
  from_email: string | null;
  category: string | null;
  priority: string | null;
  sentiment: string | null;
  status: string;
  draft_reply: string | null;
  needs_human: boolean | null;
  classification_confidence: number | null;
  assigned_team: string | null;
  reply_sent: boolean;
  created_at: string;
}

const priorityColor: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTickets()
      .then(setTickets)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold mb-6">Support Tickets</h2>

      <div className="flex gap-6">
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Subject</th>
                <th className="text-left px-4 py-3 font-medium">From</th>
                <th className="text-left px-4 py-3 font-medium">Priority</th>
                <th className="text-left px-4 py-3 font-medium">Category</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Team</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className={`border-t cursor-pointer ${selected?.id === t.id ? "bg-blue-50" : "hover:bg-gray-50"}`}
                >
                  <td className="px-4 py-3 font-medium">{t.subject || "No subject"}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{t.from_email || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${priorityColor[t.priority || ""] || "bg-gray-100"}`}>
                      {t.priority || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">{t.category || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${t.reply_sent ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">{t.assigned_team || "—"}</td>
                </tr>
              ))}
              {!loading && tickets.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">No tickets yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {selected && (
          <div className="w-96 bg-white rounded-lg shadow p-4">
            <h3 className="font-bold mb-2">{selected.subject || "No subject"}</h3>
            <div className="text-xs text-gray-500 mb-4">
              From: {selected.from_email} | {new Date(selected.created_at).toLocaleString()}
            </div>
            <div className="mb-4">
              <span className="text-xs font-medium text-gray-600">Classification</span>
              <div className="mt-1 text-sm">
                <p>Category: <strong>{selected.category}</strong></p>
                <p>Priority: <strong>{selected.priority}</strong></p>
                <p>Sentiment: <strong>{selected.sentiment}</strong></p>
                <p>Confidence: <strong>{(selected.classification_confidence ?? 0).toFixed(2)}</strong></p>
                <p>Needs Human: <strong>{selected.needs_human ? "Yes" : "No"}</strong></p>
              </div>
            </div>
            {selected.draft_reply && (
              <div>
                <span className="text-xs font-medium text-gray-600">Draft Reply</span>
                <div className="mt-1 bg-gray-50 rounded p-3 text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {selected.draft_reply}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
