"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";
import { LoginPage } from "./LoginPage";

/** Membungkus halaman: tampilkan login bila belum masuk; `adminOnly` menolak peran user. */
export function AuthGate({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const init = useAuthStore((s) => s.init);

  useEffect(() => {
    void init();
  }, [init]);

  if (status === "loading") {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Memeriksa sesi...</div>;
  }
  if (status === "anon" || !user) return <LoginPage />;
  if (adminOnly && user.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <div className="flex max-w-md flex-col items-center text-center">
          <div className="mb-4 flex size-20 items-center justify-center rounded-full bg-muted">
            <ShieldAlert className="size-9 text-[#c9cdd4]" strokeWidth={1.5} />
          </div>
          <h2 className="text-base font-semibold">Hanya untuk admin</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Akun <b>{user.username}</b> berperan <b>user</b>: dapat memakai seluruh aplikasi, tetapi manajemen pengguna,
            API key, dan pengaturan MCP hanya untuk admin.
          </p>
          <Button className="btn-primary-vigi mt-5" render={<Link href="/" />}>
            Kembali ke Design Tool
          </Button>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
