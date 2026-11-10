import App from "@/App";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, ThemeProvider } from "@/contexts";
import { I18nProvider } from "@/i18n";
import { TOKEN_KEY } from "@/lib/api";
import type { User } from "@/lib/types";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { HelmetProvider } from "react-helmet-async";
import { MemoryRouter } from "react-router";
import { server } from "./server";

export const TEST_TOKEN = "test-token";

/**
 * Mounts the real route tree (guards, layout, pages) at `path`, with the same
 * providers as main.tsx. Pass `signedInAs` to start with a stored token that
 * /auth/me resolves to that user; omit it to start signed out.
 */
export function renderApp(
  path: string,
  { signedInAs }: { signedInAs?: User } = {},
) {
  if (signedInAs) {
    localStorage.setItem(TOKEN_KEY, TEST_TOKEN);
    server.use(http.get("/api/auth/me", () => HttpResponse.json(signedInAs)));
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const user = userEvent.setup();
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
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
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return { user, ...result };
}
