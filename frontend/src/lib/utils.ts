// cn() helper — Tailwind clsx-style conditional class merging.
// We don't pull in clsx/tailwind-merge as dependencies; this is the minimal
// implementation used across the app.

export function cn(...classes: Array<string | undefined | null | false>): string {
  return classes.filter(Boolean).join(" ")
}
