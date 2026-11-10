import { z } from "zod";

export const clubSchema = z.object({
  name: z.string().trim().min(1, "Club name is required"),
  description: z.string().trim().min(1, "Description is required"),
});

export type ClubFormData = z.infer<typeof clubSchema>;
