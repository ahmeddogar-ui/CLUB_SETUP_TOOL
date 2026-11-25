import {
  NAME_PART_MAX_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
} from "@/lib/limits";
import { z } from "zod";

const tooLong = (field: string, max: number) =>
  `${field} must be at most ${max} characters`;

export const signUpSchema = z
  .object({
    fname: z
      .string()
      .trim()
      .min(1, "First name is required")
      .max(NAME_PART_MAX_LENGTH, tooLong("First name", NAME_PART_MAX_LENGTH)),
    lname: z
      .string()
      .trim()
      .min(1, "Last name is required")
      .max(NAME_PART_MAX_LENGTH, tooLong("Last name", NAME_PART_MAX_LENGTH)),
    email: z
      .string()
      .trim()
      .min(1, "Email is required")
      .email("Please enter a valid email address"),
    password: z
      .string()
      .min(
        PASSWORD_MIN_LENGTH,
        `Password must be at least ${PASSWORD_MIN_LENGTH} characters`,
      )
      .max(PASSWORD_MAX_LENGTH, tooLong("Password", PASSWORD_MAX_LENGTH)),
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type SignUpFormData = z.infer<typeof signUpSchema>;
