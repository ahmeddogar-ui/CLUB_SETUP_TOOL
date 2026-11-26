// Mirrors the limits in app/schemas.py, so forms catch an over-long value
// with a clear message before the backend rejects it.
export const CLUB_NAME_MAX_LENGTH = 100;
export const DESCRIPTION_MAX_LENGTH = 2000;
export const NOTE_MAX_LENGTH = 2000;
export const COMMENT_MAX_LENGTH = 2000;
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
// The backend stores one name of at most 100 characters: first + " " + last.
export const NAME_PART_MAX_LENGTH = 49;
export const PERSON_NAME_MAX_LENGTH = 100;
