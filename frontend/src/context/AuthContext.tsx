import { createContext, useContext, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import type { User } from "../types";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState(() => localStorage.getItem("session_token"));
  const [user, setCurrentUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : null;
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      async login(email, password) {
        const result = await authApi.login(email, password);
        localStorage.setItem("session_token", result.token);
        localStorage.setItem("user", JSON.stringify(result.user));
        setToken(result.token);
        setCurrentUser(result.user);
      },
      async register(email, password, username) {
        await authApi.register(email, password, username);
        const result = await authApi.login(email, password);
        localStorage.setItem("session_token", result.token);
        localStorage.setItem("user", JSON.stringify(result.user));
        setToken(result.token);
        setCurrentUser(result.user);
      },
      setUser(nextUser) {
        localStorage.setItem("user", JSON.stringify(nextUser));
        setCurrentUser(nextUser);
      },
      async logout() {
        if (token) {
          await authApi.logout(token).catch(() => undefined);
        }
        localStorage.removeItem("session_token");
        localStorage.removeItem("user");
        setToken(null);
        setCurrentUser(null);
      }
    }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
