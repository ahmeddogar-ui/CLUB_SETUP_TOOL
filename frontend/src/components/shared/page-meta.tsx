import { Helmet } from "react-helmet-async";

const APP_NAME = "Club Setup";

/** Sets the browser tab to "<title> · Club Setup". */
export function PageMeta({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Helmet>
      <title>{`${title} · ${APP_NAME}`}</title>
      <meta name="description" content={description} />
    </Helmet>
  );
}
