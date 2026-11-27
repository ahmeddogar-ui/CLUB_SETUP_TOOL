import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { BoxIcon, OctagonAlertIcon } from "@/icons";

export function ListError({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <Alert variant="destructive" className="m-6 w-auto p-4">
      <OctagonAlertIcon className="size-5" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

interface EmptyListProps {
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}

export function EmptyList({
  title,
  description,
  actionLabel,
  onAction,
}: EmptyListProps) {
  return (
    <div className="flex flex-col items-center justify-center border-t border-gray-100 px-6 py-12 text-center dark:border-gray-800">
      <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
        <BoxIcon className="size-6 text-gray-800 dark:text-white/90" />
      </div>
      <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
        {title}
      </h4>
      <p className="mt-1 mb-5 text-sm text-gray-500 dark:text-gray-400">
        {description}
      </p>
      <Button size="sm" variant="outline" onClick={onAction}>
        {actionLabel}
      </Button>
    </div>
  );
}
