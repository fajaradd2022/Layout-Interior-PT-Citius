import type { Metadata } from "next";
import { SettingsShell } from "@/components/settings/SettingsShell";
import { AuthGate } from "@/components/auth/AuthGate";

export const metadata: Metadata = { title: "Settings - Layout Interior Design Tool" };

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate adminOnly>
      <SettingsShell>{children}</SettingsShell>
    </AuthGate>
  );
}
