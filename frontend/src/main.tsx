import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, ThemeProvider } from "@/contexts";
import { I18nProvider } from "@/i18n";
import { ApiError, TOKEN_KEY } from "@/lib/api";
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router";
import App from "./App.tsx";
import "./index.css";

const MAX_RETRIES = 3;

const isClientError = (error: Error) =>
  error instanceof ApiError && error.status < 500;

const signOutOnUnauthorized = (error: Error) => {
  if (!(error instanceof ApiError) || error.status !== 401) return;
  if (!localStorage.getItem(TOKEN_KEY)) return;
  localStorage.removeItem(TOKEN_KEY);
  void queryClient.invalidateQueries({ queryKey: ["me"] });
};

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: signOutOnUnauthorized }),
  mutationCache: new MutationCache({ onError: signOutOnUnauthorized }),
  defaultOptions: {
    queries: {
      retry: (failureCount, error) =>
        !isClientError(error) && failureCount < MAX_RETRIES,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <HelmetProvider>
            <I18nProvider>
              <TooltipProvider>
                <AuthProvider>
                  <App />
                </AuthProvider>
              </TooltipProvider>
            </I18nProvider>
          </HelmetProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
