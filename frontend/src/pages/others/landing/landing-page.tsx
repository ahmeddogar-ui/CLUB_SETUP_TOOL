import { AppLogo } from "@/components/shared/app-logo";
import { PageMeta } from "@/components/shared/page-meta";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/contexts";
import { Link } from "react-router";

const FEATURES = [
  {
    title: "Club registration",
    description:
      "Register your club, hand in its documents and have each one reviewed.",
  },
  {
    title: "Funding and room bookings",
    description:
      "Request funding or a room for an event and follow it through approval.",
  },
  {
    title: "A full activity history",
    description:
      "Every submission, decision and note is recorded, so nothing gets lost.",
  },
];

export default function LandingPage() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <PageMeta
        title="Welcome"
        description="Register and run your UTM student club"
      />

      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-5">
        <AppLogo />
      </header>

      <main className="mx-auto w-full max-w-5xl px-6">
        <section className="py-16 text-center sm:py-24">
          <h1 className="mx-auto max-w-3xl text-4xl font-semibold text-gray-800 sm:text-5xl dark:text-white/90">
            Register and run your UTM student club in one place
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-gray-500 dark:text-gray-400">
            From the first form to your first event, Club Setup keeps your
            paperwork, approvals and history together.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {user ? (
              <Link to="/" className={buttonVariants({ size: "lg" })}>
                Go to your dashboard
              </Link>
            ) : (
              <>
                <Link to="/signup" className={buttonVariants({ size: "lg" })}>
                  Create an account
                </Link>
                <Link
                  to="/signin"
                  className={buttonVariants({ size: "lg", variant: "outline" })}
                >
                  Sign in
                </Link>
              </>
            )}
          </div>
        </section>

        <section className="grid gap-6 pb-24 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-gray-200 p-6 dark:border-gray-800 dark:bg-white/3"
            >
              <h2 className="text-lg font-medium text-gray-800 dark:text-white/90">
                {feature.title}
              </h2>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {feature.description}
              </p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
