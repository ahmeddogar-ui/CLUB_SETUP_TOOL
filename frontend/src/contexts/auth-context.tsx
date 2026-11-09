import { ApiError, apiFetch, TOKEN_KEY } from "@/lib/api";
import type { User } from "@/lib/types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useState, type ReactNode } from "react";

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
    queryFn: async () => {
      try {
        return await apiFetch<User>("/auth/me");
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          return null;
        }
        throw error;
      }
    },
    enabled: token !== null,
    retry: false,
  });

  const signIn = (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    queryClient.clear();
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
