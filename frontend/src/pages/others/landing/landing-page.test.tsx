import { LEAD } from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("landing page", () => {
  it("is where a signed-out visitor to the root lands, with sign-in and sign-up links", async () => {
    renderApp("/");

    expect(
      await screen.findByRole("heading", { level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/signin",
    );
    expect(
      screen.getByRole("link", { name: "Create an account" }),
    ).toHaveAttribute("href", "/signup");
  });

  it("still sends a signed-out visitor to any other protected page to sign in", async () => {
    renderApp("/clubs/3");

    expect(
      await screen.findByRole("heading", { name: "Sign In" }),
    ).toBeInTheDocument();
  });

  it("offers a signed-in visitor their dashboard instead of the sign-in links", async () => {
    renderApp("/welcome", { signedInAs: LEAD });

    expect(
      await screen.findByRole("link", { name: "Go to your dashboard" }),
    ).toHaveAttribute("href", "/");
    expect(
      screen.queryByRole("link", { name: "Create an account" }),
    ).not.toBeInTheDocument();
  });
});
