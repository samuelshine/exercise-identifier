import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  // Preload the subset used in critical rendering path
  display: "swap",
  variable: "--font-inter",
});

// ─── Viewport config ────────────────────────────────────────────────────────
// maximumScale: 1 prevents iOS auto-zoom on input focus (gym UX: no zooming)
// themeColor matches the manifest and the <html> background to eliminate
// the white flash on PWA launch
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#09090b",
  colorScheme: "dark",
};

// ─── Metadata ───────────────────────────────────────────────────────────────
export const metadata: Metadata = {
  title: {
    default: "Identify — Exercise Finder",
    template: "%s | Identify",
  },
  description:
    "Describe any gym exercise in your own words and instantly identify it using AI-powered biomechanics analysis. No app download required.",
  keywords: ["exercise identifier", "gym", "fitness", "workout", "AI", "exercise name"],
  authors: [{ name: "Exercise Identifier" }],
  creator: "Exercise Identifier",

  // ─── PWA / Apple ──────────────────────────────────────────────────────
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Identify",
    startupImage: [
      // iPhone 14 Pro Max
      {
        url: "/splash/splash-1290x2796.png",
        media:
          "screen and (device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3)",
      },
      // iPhone 14 / 13 / 12
      {
        url: "/splash/splash-1170x2532.png",
        media:
          "screen and (device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3)",
      },
      // iPhone SE 3rd gen
      {
        url: "/splash/splash-750x1334.png",
        media:
          "screen and (device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)",
      },
    ],
  },

  // ─── Open Graph (sharing) ──────────────────────────────────────────────
  openGraph: {
    type: "website",
    locale: "en_US",
    title: "Identify — Exercise Finder",
    description:
      "Describe or film any gym exercise and instantly identify it using AI-powered biomechanics analysis.",
    siteName: "Exercise Identifier",
  },

  // ─── Twitter Card ─────────────────────────────────────────────────────
  twitter: {
    card: "summary",
    title: "Identify — Exercise Finder",
    description: "Shazam for fitness. Identify any gym exercise instantly.",
  },

  // ─── Icons ────────────────────────────────────────────────────────────
  icons: {
    icon: [
      { url: "/icons/favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/icons/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icons/icon.svg", type: "image/svg+xml" },
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    other: [
      { rel: "mask-icon", url: "/icons/icon.svg", color: "#6366f1" },
    ],
  },

  // ─── Robots ───────────────────────────────────────────────────────────
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // `dark` class is hardcoded — dark mode only for V1 (no user toggle)
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`
          ${inter.variable}
          font-sans
          min-h-screen
          bg-surface
          text-neutral-100
          antialiased
          overscroll-none
        `}
      >
        {children}
      </body>
    </html>
  );
}
