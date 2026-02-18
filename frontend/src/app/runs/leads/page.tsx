"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listLeads } from "@/lib/api";

interface Lead {
  id: string;
  name: string;
  email: string;
  company: string | null;
  status: string;
  score: number | null;
  intent_classification: string | null;
  urgency: string | null;
  company_size_cue: string | null;
  suggested_next_step: string | null;
  qualification_summary: string | null;
  follow_up_questions: string[] | null;
  email_drafts: any[] | null;
  crm_contact_id: string | null;
  created_at: string;
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listLeads()
      .then(setLeads)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold mb-6">Sales Leads</h2>

      <div className="flex gap-6">
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Company</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">Intent</th>
                <th className="text-left px-4 py-3 font-medium">Urgency</th>
                <th className="text-left px-4 py-3 font-medium">Next Step</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr
                  key={l.id}
                  onClick={() => setSelected(l)}
                  className={`border-t cursor-pointer ${selected?.id === l.id ? "bg-blue-50" : "hover:bg-gray-50"}`}
                >
                  <td className="px-4 py-3 font-medium">{l.name}</td>
                  <td className="px-4 py-3 text-gray-500">{l.company || "—"}</td>
                  <td className="px-4 py-3">
                    {l.score != null ? (
                      <span className={`px-2 py-1 rounded text-xs ${l.score >= 70 ? "bg-green-100 text-green-700" : l.score >= 40 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700"}`}>
                        {l.score}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs">{l.intent_classification || "—"}</td>
                  <td className="px-4 py-3 text-xs">{l.urgency || "—"}</td>
                  <td className="px-4 py-3 text-xs">{l.suggested_next_step || "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${l.status === "qualified" ? "bg-green-100 text-green-700" : "bg-gray-100"}`}>
                      {l.status}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && leads.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">No leads yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {selected && (
          <div className="w-96 bg-white rounded-lg shadow p-4">
            <h3 className="font-bold mb-1">{selected.name}</h3>
            <p className="text-sm text-gray-500 mb-4">{selected.email} | {selected.company}</p>

            {selected.qualification_summary && (
              <div className="mb-4">
                <span className="text-xs font-medium text-gray-600">Qualification Summary</span>
                <p className="mt-1 text-sm">{selected.qualification_summary}</p>
              </div>
            )}

            <div className="mb-4">
              <span className="text-xs font-medium text-gray-600">Details</span>
              <div className="mt-1 text-sm">
                <p>Score: <strong>{selected.score ?? "—"}</strong></p>
                <p>Size: <strong>{selected.company_size_cue}</strong></p>
                <p>CRM ID: <strong>{selected.crm_contact_id || "Not synced"}</strong></p>
              </div>
            </div>

            {selected.follow_up_questions && selected.follow_up_questions.length > 0 && (
              <div className="mb-4">
                <span className="text-xs font-medium text-gray-600">Follow-up Questions</span>
                <ul className="mt-1 text-sm list-disc pl-4">
                  {selected.follow_up_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </div>
            )}

            {selected.email_drafts && selected.email_drafts.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-600">Email Drafts ({selected.email_drafts.length})</span>
                {selected.email_drafts.map((d: any, i: number) => (
                  <div key={i} className="mt-2 bg-gray-50 rounded p-2 text-xs">
                    <p className="font-medium">{d.subject}</p>
                    <p className="mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">{d.body?.substring(0, 200)}...</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
