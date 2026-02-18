"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listTenants, createTenant, updateTenant, deleteTenant } from "@/lib/api";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  has_anthropic_key: boolean;
  max_runs_per_day: number;
  max_tokens_per_day: number;
  support_workflow_enabled: boolean;
  sales_workflow_enabled: boolean;
  autosend_enabled: boolean;
  confidence_threshold: number;
  created_at: string;
}

export default function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    name: "",
    slug: "",
    anthropic_api_key: "",
    max_runs_per_day: 500,
    max_tokens_per_day: 500000,
  });

  const load = async () => {
    setLoading(true);
    try {
      const data = await listTenants();
      setTenants(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createTenant(form);
      setShowCreate(false);
      setForm({ name: "", slug: "", anthropic_api_key: "", max_runs_per_day: 500, max_tokens_per_day: 500000 });
      load();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleToggle = async (tenant: Tenant, field: string) => {
    try {
      await updateTenant(tenant.id, { [field]: !(tenant as any)[field] });
      load();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (tenant: Tenant) => {
    if (!confirm(`Deactivate tenant "${tenant.name}"?`)) return;
    try {
      await deleteTenant(tenant.id);
      load();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <AdminLayout>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Tenants</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700"
        >
          {showCreate ? "Cancel" : "+ New Tenant"}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Slug</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "") })}
                placeholder="my-company"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Anthropic API Key</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="password"
                value={form.anthropic_api_key}
                onChange={(e) => setForm({ ...form, anthropic_api_key: e.target.value })}
                placeholder="sk-ant-..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max Runs/Day</label>
              <input
                className="w-full border rounded px-3 py-2 text-sm"
                type="number"
                value={form.max_runs_per_day}
                onChange={(e) => setForm({ ...form, max_runs_per_day: parseInt(e.target.value) })}
              />
            </div>
          </div>
          <button type="submit" className="mt-4 bg-green-600 text-white px-4 py-2 rounded text-sm">
            Create Tenant
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Slug</th>
                <th className="text-left px-4 py-3 font-medium">API Key</th>
                <th className="text-left px-4 py-3 font-medium">Support</th>
                <th className="text-left px-4 py-3 font-medium">Sales</th>
                <th className="text-left px-4 py-3 font-medium">Autosend</th>
                <th className="text-left px-4 py-3 font-medium">Limits</th>
                <th className="text-left px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="px-4 py-3 font-medium">{t.name}</td>
                  <td className="px-4 py-3 text-gray-500">{t.slug}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${t.has_anthropic_key ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {t.has_anthropic_key ? "Set" : "Missing"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleToggle(t, "support_workflow_enabled")}
                      className={`px-2 py-1 rounded text-xs ${t.support_workflow_enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {t.support_workflow_enabled ? "ON" : "OFF"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleToggle(t, "sales_workflow_enabled")}
                      className={`px-2 py-1 rounded text-xs ${t.sales_workflow_enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {t.sales_workflow_enabled ? "ON" : "OFF"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${t.autosend_enabled ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-500"}`}>
                      {t.autosend_enabled ? "ON" : "OFF"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {t.max_runs_per_day} runs/day
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(t)}
                      className="text-red-600 text-xs hover:underline"
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))}
              {tenants.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    No tenants yet. Create one to get started.
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
