import { PageMeta } from "@/components/shared/page-meta";
import Error404 from "./index";

export default function Error404Page() {
  return (
    <div>
      <PageMeta
        title="Page not found | Club Setup"
        description="The page you are looking for does not exist"
      />
      <Error404 />
    </div>
  );
}
