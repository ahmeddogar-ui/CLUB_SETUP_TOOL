import { expect, test, type Page } from "@playwright/test";
import { promoteToAdmin } from "./database.ts";

// One journey through the real stack (Vite proxy, FastAPI, Postgres). Unique
// emails per run, so the database never needs resetting between runs.
const runId = Date.now();
const PASSWORD = "e2e-password";
const lead = {
  first: "Lena",
  last: "Lead",
  email: `lead-${runId}@example.com`,
};
const admin = {
  first: "Ada",
  last: "Admin",
  email: `admin-${runId}@example.com`,
};
const CLUB_NAME = `Chess Club ${runId}`;
const DOCUMENTS = ["Constitution", "Executive list", "Budget", "Advisor form"];
const ALL_REQUIREMENTS = [
  ...DOCUMENTS,
  "Bank account setup",
  "Executive onboarding",
];

async function signUp(page: Page, person: typeof lead) {
  await page.goto("/signup");
  await page.getByLabel(/^first name/i).fill(person.first);
  await page.getByLabel(/^last name/i).fill(person.last);
  await page.getByLabel(/^email/i).fill(person.email);
  await page.getByLabel(/^password/i).fill(PASSWORD);
  await page.getByLabel(/^confirm password/i).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign Up" }).click();
  await expect(page.getByText("Account created")).toBeVisible();
}

async function signIn(page: Page, email: string, landingHeading: string) {
  await page.goto("/signin");
  await page.getByLabel(/^email/i).fill(email);
  await page.getByLabel(/^password/i).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(
    page.getByRole("heading", { name: landingHeading }),
  ).toBeVisible();
}

function requirementRow(page: Page, label: string) {
  return page.getByRole("row", { name: new RegExp(`^${label}`) });
}

test("a lead's club goes from draft to approved by an admin", async ({
  browser,
}) => {
  const leadPage = await (await browser.newContext()).newPage();
  const adminPage = await (await browser.newContext()).newPage();

  await test.step("lead signs up and creates a club", async () => {
    await signUp(leadPage, lead);
    await signIn(leadPage, lead.email, "My clubs");

    await leadPage.getByRole("button", { name: /new club/i }).click();
    await leadPage.getByLabel(/club name/i).fill(CLUB_NAME);
    await leadPage.getByLabel(/description/i).fill("We play chess");
    await leadPage.getByRole("button", { name: "Create club" }).click();
    await expect(
      leadPage.getByRole("heading", { name: CLUB_NAME }),
    ).toBeVisible();
  });

  await test.step("submitting is blocked until every document is linked", async () => {
    await leadPage.getByRole("button", { name: "Submit for review" }).click();
    await expect(leadPage.getByText(/^missing: constitution/)).toBeVisible();

    for (const document of DOCUMENTS) {
      await requirementRow(leadPage, document)
        .getByRole("button", { name: "Provide link" })
        .click();
      await leadPage
        .getByLabel(/document link/i)
        .fill(`https://docs.example.com/${runId}/${document}`);
      await leadPage.getByRole("button", { name: "Save link" }).click();
      await expect(
        requirementRow(leadPage, document).getByText("Provided"),
      ).toBeVisible();
    }

    await leadPage.getByRole("button", { name: "Submit for review" }).click();
    await expect(
      leadPage.getByText("Submitted", { exact: true }),
    ).toBeVisible();
  });

  await test.step("admin reviews and approves", async () => {
    await signUp(adminPage, admin);
    promoteToAdmin(admin.email);
    await signIn(adminPage, admin.email, "All clubs");

    await adminPage.goto("/review");
    await adminPage.getByRole("link", { name: CLUB_NAME }).click();
    await adminPage.getByRole("button", { name: "Start review" }).click();
    await expect(
      adminPage.getByText("Under review", { exact: true }),
    ).toBeVisible();

    for (const requirement of ALL_REQUIREMENTS) {
      await requirementRow(adminPage, requirement)
        .getByRole("button", { name: "Approve" })
        .click();
      await adminPage
        .getByRole("dialog")
        .getByRole("button", { name: "Approve" })
        .click();
      await expect(
        requirementRow(adminPage, requirement).getByText("Approved"),
      ).toBeVisible();
    }

    await adminPage.getByRole("button", { name: "Approve club" }).click();
    await expect(
      adminPage.getByText("Approved", { exact: true }).first(),
    ).toBeVisible();
  });

  await test.step("lead sees the approval and its history", async () => {
    await leadPage.reload();
    await expect(leadPage.getByText("Club approved")).toBeVisible();
    await expect(
      leadPage.getByRole("button", { name: /submit/i }),
    ).not.toBeVisible();
  });
});
