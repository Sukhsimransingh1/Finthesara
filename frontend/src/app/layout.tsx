
import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/shell";
import { ProjectProvider } from "@/components/projects/ProjectProvider";

export const metadata: Metadata = {
  title: "Finthesara | Financial Intelligence",
  description: "Evidence-led financial research workspace",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ProjectProvider>
          <Shell>{children}</Shell>
        </ProjectProvider>
      </body>
    </html>
  );
}
