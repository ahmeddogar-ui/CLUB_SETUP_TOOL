import { PageMeta } from "@/components/shared/page-meta";
import SignUp from "./index";

export default function SignUpPage() {
  return (
    <>
      <PageMeta
        title="Sign up | Club Setup"
        description="Create a Club Setup account"
      />
      <SignUp />
    </>
  );
}
