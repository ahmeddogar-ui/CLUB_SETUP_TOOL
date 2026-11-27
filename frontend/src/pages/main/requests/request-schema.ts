import {
  LINE_ITEM_DESCRIPTION_MAX_LENGTH,
  MAX_BOOKING_HOURS,
  MAX_LINE_ITEM_CENTS,
  MAX_LINE_ITEMS,
  REQUEST_TITLE_MAX_LENGTH,
} from "@/lib/limits";
import { formatCents } from "@/lib/request-labels";
import type { RequestDetail, RequestInput } from "@/lib/request-types";
import { z } from "zod";

const CENTS_PER_DOLLAR = 100;
const MINUTES_PER_HOUR = 60;
const MS_PER_HOUR = MINUTES_PER_HOUR * 60 * 1000;
// Whole dollars, optionally with one or two decimals.
const AMOUNT_PATTERN = /^\d+(\.\d{1,2})?$/;

/** "125.50" -> 12550, or null when it isn't dollars and cents. */
export function parseAmountCents(amount: string): number | null {
  const trimmed = amount.trim();
  if (!AMOUNT_PATTERN.test(trimmed)) return null;
  return Math.round(Number(trimmed) * CENTS_PER_DOLLAR);
}

function parseLocalDateTime(date: string, time: string): Date {
  return new Date(`${date}T${time}`);
}

function amountError(amount: string): string | null {
  const cents = parseAmountCents(amount);
  if (cents === null) return "Enter dollars and cents, like 125.50";
  if (cents <= 0) return "Amount must be more than $0.00";
  if (cents > MAX_LINE_ITEM_CENTS) {
    return `Amount can be at most ${formatCents(MAX_LINE_ITEM_CENTS)}`;
  }
  return null;
}

// One flat shape for both request types, so the type can be switched without
// losing what was typed; only the chosen type's fields are validated. Every
// rule lives in superRefine because zod skips it when the shape itself fails.
export const requestFormSchema = z
  .object({
    request_type: z.enum(["funding", "room_booking"]),
    title: z.string(),
    line_items: z
      .array(z.object({ description: z.string(), amount: z.string() }))
      .min(1)
      .max(MAX_LINE_ITEMS),
    room_id: z.string(),
    date: z.string(),
    start_time: z.string(),
    end_time: z.string(),
  })
  .superRefine((form, context) => {
    const report = (path: (string | number)[], message: string) =>
      context.addIssue({ code: z.ZodIssueCode.custom, path, message });

    const title = form.title.trim();
    if (!title) report(["title"], "Title is required");
    if (title.length > REQUEST_TITLE_MAX_LENGTH) {
      report(
        ["title"],
        `Title must be at most ${REQUEST_TITLE_MAX_LENGTH} characters`,
      );
    }

    if (form.request_type === "funding") {
      form.line_items.forEach((item, index) => {
        const description = item.description.trim();
        if (!description) {
          report(
            ["line_items", index, "description"],
            "Description is required",
          );
        } else if (description.length > LINE_ITEM_DESCRIPTION_MAX_LENGTH) {
          report(
            ["line_items", index, "description"],
            `Description must be at most ${LINE_ITEM_DESCRIPTION_MAX_LENGTH} characters`,
          );
        }
        const message = amountError(item.amount);
        if (message) report(["line_items", index, "amount"], message);
      });
      return;
    }

    if (!form.room_id) report(["room_id"], "Choose a room");
    if (!form.date) report(["date"], "Choose a date");
    if (!form.start_time) report(["start_time"], "Choose a start time");
    if (!form.end_time) report(["end_time"], "Choose an end time");
    if (!form.date || !form.start_time || !form.end_time) return;

    const starts = parseLocalDateTime(form.date, form.start_time);
    const ends = parseLocalDateTime(form.date, form.end_time);
    if (ends <= starts) {
      report(["end_time"], "End time must be after the start time");
    } else if (
      ends.getTime() - starts.getTime() >
      MAX_BOOKING_HOURS * MS_PER_HOUR
    ) {
      report(
        ["end_time"],
        `A booking can be at most ${MAX_BOOKING_HOURS} hours`,
      );
    }
  });

export type RequestFormValues = z.infer<typeof requestFormSchema>;

export const EMPTY_REQUEST_FORM: RequestFormValues = {
  request_type: "funding",
  title: "",
  line_items: [{ description: "", amount: "" }],
  room_id: "",
  date: "",
  start_time: "",
  end_time: "",
};

/** The validated form as the backend's request body. */
export function toRequestInput(form: RequestFormValues): RequestInput {
  if (form.request_type === "funding") {
    return {
      title: form.title.trim(),
      details: {
        request_type: "funding",
        line_items: form.line_items.map((item) => ({
          description: item.description.trim(),
          amount_cents: parseAmountCents(item.amount) ?? 0,
        })),
      },
    };
  }

  return {
    title: form.title,
    details: {
      request_type: "room_booking",
      room_id: Number(form.room_id),
      starts_at: parseLocalDateTime(form.date, form.start_time).toISOString(),
      ends_at: parseLocalDateTime(form.date, form.end_time).toISOString(),
    },
  };
}

const pad = (value: number) => String(value).padStart(2, "0");

/** A saved request as form values, for editing. */
export function toFormValues(request: RequestDetail): RequestFormValues {
  const { details } = request;
  if (details.request_type === "funding") {
    return {
      ...EMPTY_REQUEST_FORM,
      request_type: "funding",
      title: request.title,
      line_items: details.line_items.map((item) => ({
        description: item.description,
        amount: (item.amount_cents / CENTS_PER_DOLLAR).toFixed(2),
      })),
    };
  }

  const starts = new Date(details.starts_at);
  const ends = new Date(details.ends_at);
  return {
    ...EMPTY_REQUEST_FORM,
    request_type: "room_booking",
    title: request.title,
    room_id: String(details.room_id),
    date: `${starts.getFullYear()}-${pad(starts.getMonth() + 1)}-${pad(starts.getDate())}`,
    start_time: `${pad(starts.getHours())}:${pad(starts.getMinutes())}`,
    end_time: `${pad(ends.getHours())}:${pad(ends.getMinutes())}`,
  };
}
