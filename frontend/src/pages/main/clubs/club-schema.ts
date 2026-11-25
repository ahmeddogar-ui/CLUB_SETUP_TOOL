import { CLUB_NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH } from "@/lib/limits";
import { z } from "zod";

export const clubSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Club name is required")
    .max(
      CLUB_NAME_MAX_LENGTH,
      `Club name must be at most ${CLUB_NAME_MAX_LENGTH} characters`,
    ),
  description: z
    .string()
    .trim()
    .min(1, "Description is required")
    .max(
      DESCRIPTION_MAX_LENGTH,
      `Description must be at most ${DESCRIPTION_MAX_LENGTH} characters`,
    ),
});

export type ClubFormData = z.infer<typeof clubSchema>;
