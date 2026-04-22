import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Identify — Exercise Finder",
  description:
    "Describe any gym exercise in your own words and instantly identify it using AI-powered biomechanics analysis.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface text-neutral-100 antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
