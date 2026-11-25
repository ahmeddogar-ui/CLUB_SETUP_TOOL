import GridShape from "@/components/shared/grid-shape";
import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Link } from "react-router";

export default function Error404Page() {
  return (
    <div className="relative z-1 flex min-h-screen flex-col items-center justify-center overflow-hidden p-6">
      <PageMeta
        title="Page not found | Club Setup"
        description="The page you are looking for does not exist"
      />
      <GridShape />
      <div className="mx-auto w-full max-w-60.5 text-center sm:max-w-118">
        <h1 className="mb-8 font-bold text-gray-800 dark:text-white/90">
          ERROR
        </h1>

        <img
          src="/images/error/404.svg"
          alt="404"
          className="dark:hidden"
          width={472}
          height={152}
        />
        <img
          src="/images/error/404-dark.svg"
          alt="404"
          className="hidden dark:block"
          width={472}
          height={152}
        />

        <p className="mt-10 mb-6 text-base text-gray-700 sm:text-lg dark:text-gray-400">
          We can’t seem to find the page you are looking for!
        </p>

        <Button
          size="lg"
          variant="outline"
          className="h-12.5 bg-white"
          nativeButton={false}
          render={<Link to="/" />}
        >
          Back to Home Page
        </Button>
      </div>

      <p className="absolute inset-s-1/2 bottom-6 -translate-x-1/2 text-center text-sm text-gray-500 dark:text-gray-400">
        &copy; {new Date().getFullYear()} - Club Setup
      </p>
    </div>
  );
}
