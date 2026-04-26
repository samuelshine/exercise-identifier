import Link from "next/link";
import { Compass } from "lucide-react";

export const metadata = {
  title: "Not found",
};

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 ring-1 ring-accent/20">
        <Compass className="h-7 w-7 text-accent" aria-hidden="true" />
      </div>

      <h1 className="mt-4 text-3xl font-bold tracking-tight text-neutral-100">
        404
      </h1>
      <p className="mt-1 text-sm font-medium text-neutral-300">Page not found</p>
      <p className="mt-1 max-w-xs text-sm text-neutral-500">
        The exercise or page you're looking for doesn't exist or has moved.
      </p>

      <Link
        href="/"
        className="mt-6 inline-flex items-center justify-center rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-neutral-950 transition-colors hover:bg-accent/90 active:scale-[0.98] no-select"
      >
        Back to search
      </Link>
    </main>
  );
}
