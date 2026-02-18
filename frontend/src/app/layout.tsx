import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "B2B Workflow Automation - Admin",
  description: "Multi-tenant workflow automation admin panel",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
