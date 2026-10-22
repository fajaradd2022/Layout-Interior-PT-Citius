"use client";

import { create } from "zustand";
import { authApi, clearToken, getToken, setToken, type AuthUser } from "@/lib/api";

type Status = "loading" | "anon" | "authed";

interface AuthState {
  status: Status;
  user: AuthUser | null;
  error: string | null;
  init: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  changePassword: (oldPw: string, newPw: string) => Promise<void>;
  isAdmin: () => boolean;
}

let initPromise: Promise<void> | null = null;

export const useAuthStore = create<AuthState>()((set, get) => ({
  status: "loading",
  user: null,
  error: null,

  init: () => {
    if (initPromise) return initPromise;
    initPromise = (async () => {
      if (!getToken()) {
        set({ status: "anon", user: null });
        return;
      }
      try {
        const { user } = await authApi.me();
        set({ status: "authed", user, error: null });
      } catch (e) {
        const msg = (e as Error).message;
        // token tidak valid / kedaluwarsa -> ke halaman login; backend mati -> tampilkan pesan
        if (/perlu login|unauthenticated|401/i.test(msg)) clearToken();
        set({ status: "anon", user: null, error: /Backend tidak dapat dihubungi/.test(msg) ? msg : null });
      } finally {
        initPromise = null;
      }
    })();
    return initPromise;
  },
  login: async (username, password) => {
    set({ error: null });
    try {
      const { token, user } = await authApi.login(username, password);
      setToken(token);
      set({ status: "authed", user });
    } catch (e) {
      set({ error: (e as Error).message });
      throw e;
    }
  },
  logout: async () => {
    try {
      await authApi.logout();
    } catch {
      /* abaikan */
    }
    clearToken();
    set({ status: "anon", user: null });
  },
  changePassword: async (oldPw, newPw) => {
    await authApi.changePassword(oldPw, newPw);
  },
  isAdmin: () => get().user?.role === "admin",
}));

if (typeof window !== "undefined") {
  // dikirim oleh klien API saat server menjawab 401 (sesi kedaluwarsa / dicabut)
  window.addEventListener("li-auth-expired", () => {
    clearToken();
    useAuthStore.setState({ status: "anon", user: null, error: "Sesi berakhir, silakan login lagi." });
  });
}
