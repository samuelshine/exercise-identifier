import type { MetadataRoute } from "next";

// Refresh daily — exercise taxonomy is mostly static between deploys,
// but new exercises do get added to the dataset.
export const revalidate = 86400;

interface PaginatedExercise {
  slug: string;
  // updated_at isn't on ExerciseSummary; we fall back to lastModified=now()
}

interface PaginatedList {
  total: number;
  pages: number;
  results: PaginatedExercise[];
}

/**
 * Dynamic sitemap.
 *
 * Walks the paginated /exercises list to enumerate every detail page.
 * If the backend is unreachable at build time we still emit the home
 * page so the deploy doesn't fail.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "http://localhost:3000";
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

  const now = new Date();
  const home: MetadataRoute.Sitemap = [
    { url: siteUrl, lastModified: now, changeFrequency: "weekly", priority: 1 },
  ];

  let exercises: PaginatedExercise[] = [];
  try {
    const perPage = 100;
    let page = 1;
    while (true) {
      const res = await fetch(
        `${apiUrl}/exercises?page=${page}&per_page=${perPage}`,
        { next: { revalidate: 86400 } }
      );
      if (!res.ok) break;
      const data = (await res.json()) as PaginatedList;
      exercises = exercises.concat(data.results);
      if (page >= data.pages) break;
      page += 1;
    }
  } catch {
    // Build-time fetch failure — return only the home entry.
    return home;
  }

  return [
    ...home,
    ...exercises.map((ex) => ({
      url: `${siteUrl}/exercise/${ex.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}
