"use client";

import { useState } from "react";
import { Loader2, LogIn, Map } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/auth-store";
import { API_BASE } from "@/lib/api";

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const error = useAuthStore((s) => s.error);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(username.trim(), password);
    } catch {
      /* pesan sudah di store */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border bg-card p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <span className="flex size-9 items-center justify-center rounded-lg bg-[#00b386] text-white">
            <Map className="size-5" />
          </span>
          <div>
            <h1 className="text-base font-semibold">Layout Interior Design Tool</h1>
            <p className="text-xs text-muted-foreground">PT Citius - masuk untuk melanjutkan</p>
          </div>
        </div>
        <div className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="username">Username</Label>
            <Input id="username" autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="password">Kata sandi</Label>
            <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
          <Button type="submit" className="btn-primary-vigi" disabled={busy || !username || !password}>
            {busy ? <Loader2 className="animate-spin" /> : <LogIn />} Masuk
          </Button>
        </div>
        <p className="mt-5 text-[11px] text-muted-foreground">
          Backend: {API_BASE}. Akun bawaan saat pertama kali dijalankan: <code>admin</code> / <code>admin123</code> (segera ubah di menu profil).
        </p>
      </form>
    </div>
  );
}
