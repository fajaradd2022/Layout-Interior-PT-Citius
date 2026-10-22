"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Loader2, MoreVertical, Plus, Trash2, UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { usersApi, type AuthUser } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { formatDate, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

type Role = "admin" | "user";

export function UsersView() {
  const me = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<AuthUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [edit, setEdit] = useState<AuthUser | null>(null);
  const [reset, setReset] = useState<AuthUser | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await usersApi.list());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await load();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Users</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Kelola akun pengguna aplikasi. <b>Admin</b> dapat mengelola pengguna dan seluruh pengaturan (API key, Instance-level MCP).{" "}
          <b>User</b> dapat memakai seluruh aplikasi (proyek, denah, perangkat, kabel, export) tetapi tidak dapat membuka manajemen pengguna dan pengaturan MCP.
        </p>
      </div>
      {error && <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 border-b-2 border-[#00b386] px-1 pb-2 text-sm font-medium">
          Semua pengguna <span className="rounded-full bg-muted px-2 text-xs">{users?.length ?? 0}</span>
        </div>
        <Button className="btn-primary-vigi ml-auto" onClick={() => setCreateOpen(true)}>
          <Plus /> Tambah pengguna
        </Button>
      </div>
      <div className="overflow-hidden rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-4 py-2.5 font-medium">Pengguna</th>
              <th className="px-4 py-2.5 font-medium">Peran</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5 font-medium">Login terakhir</th>
              <th className="px-4 py-2.5 font-medium">Dibuat</th>
              <th className="w-10 px-2 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {users === null && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted-foreground">
                  <Loader2 className="mr-2 inline size-4 animate-spin" /> Memuat...
                </td>
              </tr>
            )}
            {users?.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="px-4 py-3">
                  <div className="font-medium">
                    {u.name || u.username}
                    {u.id === me?.id && <span className="ml-2 rounded-full bg-accent px-1.5 text-[10px] text-accent-foreground">Anda</span>}
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">@{u.username}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", u.role === "admin" ? "bg-[#00b386]/15 text-[#00795a]" : "bg-muted text-muted-foreground")}>
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">{u.active ? "Aktif" : <span className="text-destructive">Nonaktif</span>}</td>
                <td className="px-4 py-3 text-muted-foreground">{u.last_login_at ? timeAgo(u.last_login_at) : "Belum pernah"}</td>
                <td className="px-4 py-3 text-muted-foreground">{formatDate(u.created_at)}</td>
                <td className="px-2 py-3">
                  <DropdownMenu>
                    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Aksi" />}>
                      <MoreVertical />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => setEdit(u)}>
                        <UserCog /> Ubah nama / peran / status
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setReset(u)}>
                        <KeyRound /> Reset kata sandi
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        variant="destructive"
                        disabled={u.id === me?.id}
                        onClick={() => {
                          if (confirm(`Hapus pengguna @${u.username}?`)) void act(() => usersApi.remove(u.id));
                        }}
                      >
                        <Trash2 /> Hapus
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">{createOpen && <CreateUserBody onDone={() => void act(load).then(() => setCreateOpen(false))} onClose={() => setCreateOpen(false)} />}</DialogContent>
      </Dialog>
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="sm:max-w-md">{edit && <EditUserBody user={edit} self={edit.id === me?.id} onDone={() => void act(load).then(() => setEdit(null))} onClose={() => setEdit(null)} />}</DialogContent>
      </Dialog>
      <Dialog open={!!reset} onOpenChange={(o) => !o && setReset(null)}>
        <DialogContent className="sm:max-w-md">{reset && <ResetPasswordBody user={reset} onDone={() => setReset(null)} onClose={() => setReset(null)} />}</DialogContent>
      </Dialog>
    </div>
  );
}

function RoleSelect({ value, onChange, disabled }: { value: Role; onChange: (r: Role) => void; disabled?: boolean }) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value as Role)}
      className="h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-60"
    >
      <option value="user">user - pengguna aplikasi</option>
      <option value="admin">admin - kelola pengguna & pengaturan MCP</option>
    </select>
  );
}

function CreateUserBody({ onDone, onClose }: { onDone: () => void; onClose: () => void }) {
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  return (
    <>
      <DialogHeader>
        <DialogTitle>Tambah pengguna</DialogTitle>
        <DialogDescription>Username minimal 3 karakter, kata sandi minimal 6 karakter.</DialogDescription>
      </DialogHeader>
      <div className="grid gap-3">
        <div className="grid gap-1.5">
          <Label>Username</Label>
          <Input autoFocus value={username} onChange={(e) => setUsername(e.target.value.toLowerCase())} placeholder="mis. budi" />
        </div>
        <div className="grid gap-1.5">
          <Label>Nama lengkap</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Kata sandi</Label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Peran</Label>
          <RoleSelect value={role} onChange={setRole} />
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Batal
        </Button>
        <Button
          className="btn-primary-vigi"
          disabled={busy || username.length < 3 || password.length < 6}
          onClick={async () => {
            setBusy(true);
            setErr(null);
            try {
              await usersApi.create({ username, name, password, role });
              onDone();
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? <Loader2 className="animate-spin" /> : null} Simpan
        </Button>
      </DialogFooter>
    </>
  );
}

function EditUserBody({ user, self, onDone, onClose }: { user: AuthUser; self: boolean; onDone: () => void; onClose: () => void }) {
  const [name, setName] = useState(user.name);
  const [role, setRole] = useState<Role>(user.role);
  const [active, setActive] = useState(user.active);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  return (
    <>
      <DialogHeader>
        <DialogTitle>Ubah pengguna @{user.username}</DialogTitle>
        <DialogDescription>{self ? "Anda tidak dapat menonaktifkan akun sendiri." : "Pengguna nonaktif tidak bisa login."}</DialogDescription>
      </DialogHeader>
      <div className="grid gap-3">
        <div className="grid gap-1.5">
          <Label>Nama lengkap</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label>Peran</Label>
          <RoleSelect value={role} onChange={setRole} />
        </div>
        <div className="flex items-center justify-between rounded-lg border px-3 py-2">
          <Label className="text-sm">Aktif</Label>
          <Switch checked={active} disabled={self} onCheckedChange={(c) => setActive(Boolean(c))} />
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Batal
        </Button>
        <Button
          className="btn-primary-vigi"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setErr(null);
            try {
              await usersApi.update(user.id, { name, role, active });
              onDone();
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? <Loader2 className="animate-spin" /> : null} Simpan
        </Button>
      </DialogFooter>
    </>
  );
}

function ResetPasswordBody({ user, onDone, onClose }: { user: AuthUser; onDone: () => void; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  return (
    <>
      <DialogHeader>
        <DialogTitle>Reset kata sandi @{user.username}</DialogTitle>
        <DialogDescription>Sesi lain milik pengguna ini akan diputus setelah kata sandi diganti.</DialogDescription>
      </DialogHeader>
      <div className="grid gap-1.5">
        <Label>Kata sandi baru</Label>
        <Input autoFocus type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      {err && <p className="text-sm text-destructive">{err}</p>}
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          Batal
        </Button>
        <Button
          className="btn-primary-vigi"
          disabled={busy || password.length < 6}
          onClick={async () => {
            setBusy(true);
            setErr(null);
            try {
              await usersApi.update(user.id, { password });
              onDone();
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? <Loader2 className="animate-spin" /> : null} Simpan
        </Button>
      </DialogFooter>
    </>
  );
}
