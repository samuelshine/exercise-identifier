import type { MetadataRoute } from "next";

/**
 * robots.txt — generated at build time by Next.js.
 *
 * NEXT_PUBLIC_SITE_URL must be set in production (e.g. https://identify.app).
 * Falls back to localhost so local builds don't publish a stub URL.
 */
export default function robots(): MetadataRoute.Robots {
  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "http://localhost:3000";

  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: ["/api/"] },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
