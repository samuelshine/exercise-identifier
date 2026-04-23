import withPWAInit from "@ducanh2912/next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  // Disable in dev — service workers interfere with hot reload
  disable: process.env.NODE_ENV === "development",
  // Cache the app shell on install
  cacheOnFrontEndNav: true,
  aggressiveFrontEndNavCaching: true,
  reloadOnOnline: true,
  // Custom workbox config
  workboxOptions: {
    // Precache the compiled JS/CSS bundles
    disableDevLogs: true,
  },
  // Runtime caching strategies (augments workbox defaults)
  // API responses: network-first (fresh data preferred, stale fallback)
  // Static assets: cache-first (icons, fonts don't change between deploys)
  runtimeCaching: [
    {
      // API: text + video search endpoints
      urlPattern: /^https?:\/\/.*\/search\/.*/i,
      handler: "NetworkFirst",
      options: {
        cacheName: "api-search-cache",
        expiration: { maxEntries: 50, maxAgeSeconds: 300 },
        networkTimeoutSeconds: 10,
      },
    },
    {
      // API: exercise detail and list endpoints
      urlPattern: /^https?:\/\/.*\/exercises\/.*/i,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "api-exercises-cache",
        expiration: { maxEntries: 200, maxAgeSeconds: 3600 },
      },
    },
    {
      // Google Fonts stylesheets
      urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
      handler: "StaleWhileRevalidate",
      options: { cacheName: "google-fonts-stylesheets" },
    },
    {
      // Google Fonts files (woff2)
      urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
      handler: "CacheFirst",
      options: {
        cacheName: "google-fonts-webfonts",
        expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
      },
    },
    {
      // Static images and icons — cache-first, long TTL
      urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
      handler: "CacheFirst",
      options: {
        cacheName: "static-image-cache",
        expiration: { maxEntries: 64, maxAgeSeconds: 60 * 60 * 24 * 30 },
      },
    },
  ],
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default withPWA(nextConfig);
