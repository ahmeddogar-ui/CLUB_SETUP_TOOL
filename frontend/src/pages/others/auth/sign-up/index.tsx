import { Link } from "react-router";
import { cn } from "@/utils";
import SignUpFormFields from "./form";
import SignUpHeader from "./header";

export default function SignUp() {
  return (
    <div
      className={cn(
        "no-scrollbar flex w-full flex-1 flex-col overflow-y-auto lg:w-1/2",
      )}
    >
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center">
        <div>
          <SignUpHeader />

          <div>
            <SignUpFormFields />

            <div className="mt-5">
              <p className="text-center text-sm font-normal text-gray-700 sm:text-start dark:text-gray-400">
                Already have an account?{" "}
                <Link
                  to="/signin"
                  className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                >
                  Sign In
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
