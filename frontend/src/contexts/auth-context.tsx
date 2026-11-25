import { apiFetch, SESSION_EXPIRED_EVENT, TOKEN_KEY } from "@/lib/api";
import type { User } from "@/lib/types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));

  const { data: user, isLoading } = useQuery({
    queryKey: ["me", token],
    queryFn: () => apiFetch<User>("/auth/me"),
    enabled: token !== null,
    retry: false,
  });

  const signIn = (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  };

  const signOutLocally = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    window.addEventListener(SESSION_EXPIRED_EVENT, signOutLocally);
    return () =>
      window.removeEventListener(SESSION_EXPIRED_EVENT, signOutLocally);
  }, [signOutLocally]);

  const signOut = () => {
    // Revoke the refresh cookie. Signing out locally doesn't wait for it: with
    // the access token gone the app never asks to refresh, so a failed revoke
    // leaves nothing usable behind in this browser.
    apiFetch("/auth/logout", { method: "POST" }).catch(() => undefined);
    signOutLocally();
  };

  return (
    <AuthContext.Provider
      value={{ user: user ?? null, isLoading, signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
