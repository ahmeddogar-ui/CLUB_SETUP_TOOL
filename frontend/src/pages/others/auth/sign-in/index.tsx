import { Link } from "react-router";
import { cn } from "@/utils";
import SignInFormFields from "./form";
import SignInHeader from "./header";

export default function SignIn() {
  return (
    <div className={cn("flex w-full flex-1 flex-col lg:w-1/2")}>
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center">
        <div>
          <SignInHeader />

          <div>
            <SignInFormFields />

            <div className="mt-5">
              <p className="text-center text-sm font-normal text-gray-700 sm:text-start dark:text-gray-400">
                Don&apos;t have an account?{" "}
                <Link
                  to="/signup"
                  className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                >
                  Sign Up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
