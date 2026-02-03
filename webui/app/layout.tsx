import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import "../styles/theme.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "X-Digest Admin",
  description: "Admin interface for X-News-Digest system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="motherduck">
      <body>
        <Sidebar />
        <CommandPalette />
        <main style={{ marginLeft: '240px', minHeight: '100vh', padding: '24px' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
