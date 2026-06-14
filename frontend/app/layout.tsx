import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TaxMind — GST reconciliation & filing assistant",
  description:
    "AI agent that reconciles input tax credit, flags blocked ITC with cited GST Act references, and generates GSTR-1/3B summaries.",
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
