import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  PERSON_NAME_MAX_LENGTH,
} from "@/lib/limits";
import { z } from "zod";

export const nameSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Name is required")
    .max(
      PERSON_NAME_MAX_LENGTH,
      `Name must be at most ${PERSON_NAME_MAX_LENGTH} characters`,
    ),
});

export const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required"),
    newPassword: z
      .string()
      .min(
        PASSWORD_MIN_LENGTH,
        `New password must be at least ${PASSWORD_MIN_LENGTH} characters`,
      )
      .max(
        PASSWORD_MAX_LENGTH,
        `New password must be at most ${PASSWORD_MAX_LENGTH} characters`,
      ),
    confirmPassword: z.string().min(1, "Please confirm your new password"),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type NameFormData = z.infer<typeof nameSchema>;
export type PasswordFormData = z.infer<typeof passwordSchema>;
