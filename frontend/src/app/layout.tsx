import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/shell";

export const metadata: Metadata = {
  title: "Finthesara — AI Financial Research & Intelligence",
  description:
    "Finthesara is an evidence-first financial research platform that uses AI agents to investigate companies, analyze financial information, retrieve relevant documents, verify claims, and produce traceable research reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
