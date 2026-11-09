import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, ThemeProvider } from "@/contexts";
import { I18nProvider } from "@/i18n";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HelmetProvider } from "react-helmet-async";
import { BrowserRouter } from "react-router";
import App from "./App.tsx";
import "./index.css";

const queryClient = new QueryClient();

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
