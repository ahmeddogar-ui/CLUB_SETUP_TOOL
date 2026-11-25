import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, ThemeProvider } from "@/contexts";
import { ApiError } from "@/lib/api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router";
import App from "./App.tsx";
import "./index.css";

const MAX_RETRIES = 3;

const isClientError = (error: Error) =>
  error instanceof ApiError && error.status < 500;

const queryClient = new QueryClient({
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
            <TooltipProvider>
              <AuthProvider>
                <App />
              </AuthProvider>
            </TooltipProvider>
          </HelmetProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
