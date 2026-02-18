"use client";

import { useEffect, useState } from "react";
import AdminLayout from "@/components/AdminLayout";
import { listTenants, updateTenant, getUsage } from "@/lib/api";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  support_config_yaml: string | null;
  sales_config_yaml: string | null;
  confidence_threshold: number;
  autosend_enabled: boolean;
}

export default function ConfigPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selected, setSelected] = useState<Tenant | null>(null);
  const [configType, setConfigType] = useState<"support" | "sales">("support");
  const [yaml, setYaml] = useState("");
  const [usage, setUsage] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    listTenants().then(setTenants).catch(console.error);
  }, []);

  useEffect(() => {
    if (selected) {
      const config = configType === "support"
        ? selected.support_config_yaml
        : selected.sales_config_yaml;
      setYaml(config || "# No configuration yet\n# Paste your YAML config here\n");
      getUsage(selected.id).then(setUsage).catch(() => setUsage(null));
    }
  }, [selected, configType]);

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const field = configType === "support" ? "support_config_yaml" : "sales_config_yaml";
      await updateTenant(selected.id, { [field]: yaml });
      // Refresh tenant list
      const tenants = await listTenants();
      setTenants(tenants);
      setSelected(tenants.find((t: Tenant) => t.id === selected.id) || null);
      alert("Config saved!");
    } catch (err: any) {
      alert(err.message);
    }
    setSaving(false);
  };

  return (
    <AdminLayout>
      <h2 className="text-2xl font-bold mb-6">Workflow Configuration</h2>

      <div className="flex gap-6">
        {/* Tenant selector */}
        <div className="w-56">
          <h3 className="text-sm font-medium mb-2 text-gray-600">Select Tenant</h3>
          <div className="bg-white rounded-lg shadow">
            {tenants.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelected(t)}
                className={`w-full text-left px-4 py-3 text-sm border-b last:border-b-0 ${
                  selected?.id === t.id ? "bg-blue-50 text-blue-700" : "hover:bg-gray-50"
                }`}
              >
                {t.name}
                <span className="block text-xs text-gray-400">{t.slug}</span>
              </button>
            ))}
            {tenants.length === 0 && (
              <p className="px-4 py-3 text-sm text-gray-400">No tenants</p>
            )}
          </div>
        </div>

        {/* Config editor */}
        {selected && (
          <div className="flex-1">
            <div className="flex items-center gap-4 mb-4">
              <div className="flex bg-gray-200 rounded">
                <button
                  onClick={() => setConfigType("support")}
                  className={`px-4 py-2 text-sm rounded ${configType === "support" ? "bg-blue-600 text-white" : ""}`}
                >
                  Support Config
                </button>
                <button
                  onClick={() => setConfigType("sales")}
                  className={`px-4 py-2 text-sm rounded ${configType === "sales" ? "bg-blue-600 text-white" : ""}`}
                >
                  Sales Config
                </button>
              </div>
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-green-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Config"}
              </button>
            </div>

            <textarea
              value={yaml}
              onChange={(e) => setYaml(e.target.value)}
              className="w-full h-96 bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg"
              spellCheck={false}
            />

            {/* Usage stats */}
            {usage && (
              <div className="mt-4 bg-white rounded-lg shadow p-4">
                <h4 className="text-sm font-medium mb-2">Today's Usage</h4>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <p className="text-2xl font-bold">{usage.runs_today}</p>
                    <p className="text-xs text-gray-500">Runs ({usage.max_runs_per_day} max)</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{usage.tokens_today?.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">Tokens ({usage.max_tokens_per_day?.toLocaleString()} max)</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{selected.confidence_threshold}</p>
                    <p className="text-xs text-gray-500">Confidence Threshold</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{selected.autosend_enabled ? "ON" : "OFF"}</p>
                    <p className="text-xs text-gray-500">Autosend</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
