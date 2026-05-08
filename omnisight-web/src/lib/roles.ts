export type AppRole = "admin" | "analyst" | "viewer";

export function canReview(role?: string | null) {
  return role === "admin" || role === "analyst";
}

export function isAdmin(role?: string | null) {
  return role === "admin";
}