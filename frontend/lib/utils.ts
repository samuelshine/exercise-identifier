/**
 * Conditional className utility — merges class strings, filtering falsy values.
 * Kept intentionally minimal; add clsx/tailwind-merge if conflicts arise.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
