"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken } from "@/lib/api";

const nav = [
  { href: "/tenants", label: "Tenants", icon: "🏢" },
  { href: "/runs", label: "Runs", icon: "⚡" },
  { href: "/runs/tickets", label: "Tickets", icon: "🎫" },
  { href: "/runs/leads", label: "Leads", icon: "👤" },
  { href: "/audit", label: "Audit Log", icon: "📋" },
  { href: "/config", label: "Config", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold">Workflow Admin</h1>
        <p className="text-xs text-gray-400">B2B Automation Kit</p>
      </div>
      <nav className="flex-1 p-2">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2 px-3 py-2 rounded text-sm mb-1 ${
              pathname.startsWith(item.href)
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:bg-gray-800"
            }`}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={() => {
            clearToken();
            window.location.href = "/";
          }}
          className="text-sm text-gray-400 hover:text-white"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
