import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { useAuth } from "@/contexts";
import { DetailsCard } from "./details-card";
import { PasswordCard } from "./password-card";

export default function ProfilePage() {
  const { user } = useAuth();

  // RequireAuth guarantees a user; this only narrows the type.
  if (!user) return null;

  return (
    <div>
      <PageMeta title="Profile" description="Your name and password" />
      <PageBreadcrumb pageTitle="Profile" />

      <div className="grid max-w-2xl gap-6">
        <DetailsCard user={user} />
        <PasswordCard />
      </div>
    </div>
  );
}
