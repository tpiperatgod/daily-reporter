import type { Metadata } from "next";
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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
