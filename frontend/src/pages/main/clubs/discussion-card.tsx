import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { OctagonAlertIcon } from "@/icons";
import { apiFetch } from "@/lib/api";
import { formatDateTime, USER_ROLE_LABELS } from "@/lib/labels";
import { COMMENT_MAX_LENGTH } from "@/lib/limits";
import type { Comment } from "@/lib/types";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

const COMMENTS_PAGE_SIZE = 20;

interface CommentPage {
  items: Comment[];
  total: number;
}

const commentSchema = z.object({
  body: z
    .string()
    .trim()
    .min(1, "Write a comment first")
    .max(
      COMMENT_MAX_LENGTH,
      `A comment can be at most ${COMMENT_MAX_LENGTH} characters`,
    ),
});

type CommentFormData = z.infer<typeof commentSchema>;

/** The club's thread between its lead and the admins. The API pages newest
 * first; the card shows the loaded comments oldest first, like a chat. */
export function DiscussionCard({ clubId }: { clubId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ["clubs", clubId, "comments"];

  const comments = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) =>
      apiFetch<CommentPage>(
        `/clubs/${clubId}/comments?limit=${COMMENTS_PAGE_SIZE}&offset=${pageParam}`,
      ),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce(
        (count, page) => count + page.items.length,
        0,
      );
      return loaded < lastPage.total ? loaded : undefined;
    },
  });

  const postComment = useMutation({
    mutationFn: (data: CommentFormData) =>
      apiFetch<Comment>(`/clubs/${clubId}/comments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    meta: { successMessage: "Comment posted" },
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CommentFormData>({
    resolver: zodResolver(commentSchema),
    defaultValues: { body: "" },
  });

  const oldestFirst = (comments.data?.pages ?? [])
    .flatMap((page) => page.items)
    .toReversed();

  return (
    <Card className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-6 dark:border-gray-800 dark:bg-white/3">
      <div>
        <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white/90">
          Discussion
        </CardTitle>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Questions and answers between the club lead and the reviewers.
        </p>
      </div>

      {comments.error && (
        <Alert variant="destructive" className="p-4">
          <OctagonAlertIcon className="size-5" />
          <AlertDescription>{comments.error.message}</AlertDescription>
        </Alert>
      )}

      {comments.hasNextPage && (
        <Button
          variant="outline"
          size="sm"
          className="self-start"
          disabled={comments.isFetchingNextPage}
          onClick={() => void comments.fetchNextPage()}
        >
          {comments.isFetchingNextPage ? "Loading..." : "Show older comments"}
        </Button>
      )}

      {comments.isSuccess && oldestFirst.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No comments yet. Ask a question or leave a note for the club.
        </p>
      ) : (
        <ol aria-label="Comments" className="space-y-4">
          {oldestFirst.map((comment) => (
            <CommentItem key={comment.id} comment={comment} />
          ))}
        </ol>
      )}

      <form
        onSubmit={handleSubmit((data) =>
          postComment.mutate(data, { onSuccess: () => reset() }),
        )}
        className="space-y-3"
        noValidate
      >
        {postComment.error && (
          <Alert variant="destructive" className="p-4">
            <OctagonAlertIcon className="size-5" />
            <AlertDescription>{postComment.error.message}</AlertDescription>
          </Alert>
        )}
        <Field data-invalid={Boolean(errors.body)}>
          <FieldLabel className="sr-only">Comment</FieldLabel>
          <Textarea
            {...register("body")}
            rows={3}
            placeholder="Write a comment"
            aria-invalid={errors.body ? "true" : undefined}
          />
          <FieldError errors={[errors.body]} />
        </Field>
        <div className="flex justify-end">
          <Button type="submit" size="sm" disabled={postComment.isPending}>
            {postComment.isPending ? "Posting..." : "Post comment"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function CommentItem({ comment }: { comment: Comment }) {
  return (
    <li className="rounded-xl border border-gray-100 p-4 dark:border-gray-800">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium text-gray-800 dark:text-white/90">
          {comment.author_name}
        </span>
        {comment.author_role !== "club_lead" && (
          <Badge variant="light" size="sm" color="primary">
            {USER_ROLE_LABELS[comment.author_role]}
          </Badge>
        )}
        <time
          dateTime={comment.created_at}
          className="text-xs text-gray-500 dark:text-gray-400"
        >
          {formatDateTime(comment.created_at)}
        </time>
      </div>
      <p className="mt-2 text-sm whitespace-pre-line text-gray-700 dark:text-gray-300">
        {comment.body}
      </p>
    </li>
  );
}
