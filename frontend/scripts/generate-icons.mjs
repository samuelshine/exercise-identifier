/**
 * generate-icons.mjs
 *
 * Generates all required PWA icon PNGs from the source SVG.
 * Run once after cloning, and again if icon.svg changes.
 *
 * Usage:
 *   node scripts/generate-icons.mjs
 *
 * Requires: sharp (listed in devDependencies)
 *   npm install   (sharp is already in package.json devDeps)
 */

import sharp from "sharp";
import { readFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const iconsDir = join(__dirname, "../public/icons");
const svgPath = join(iconsDir, "icon.svg");

mkdirSync(iconsDir, { recursive: true });

const svgBuffer = readFileSync(svgPath);

const icons = [
  // Standard PWA icons
  { file: "icon-192.png", size: 192, maskable: false },
  { file: "icon-512.png", size: 512, maskable: false },
  // Maskable icon: safe zone is 80% of total canvas (40px padding on 512px)
  // We add extra padding so the barbell mark sits within the safe zone
  { file: "icon-maskable-512.png", size: 512, maskable: true },
  // Apple touch icon (referenced in layout <head>)
  { file: "apple-touch-icon.png", size: 180, maskable: false },
  // Favicon sizes
  { file: "favicon-32.png", size: 32, maskable: false },
  { file: "favicon-16.png", size: 16, maskable: false },
];

for (const { file, size, maskable } of icons) {
  const outputPath = join(iconsDir, file);

  if (maskable) {
    // For maskable: render SVG centered on a slightly larger canvas
    // so the icon mark fits within the 80% safe zone
    const canvasSize = size;
    const iconSize = Math.round(size * 0.75); // 75% of canvas = within safe zone
    const offset = Math.round((canvasSize - iconSize) / 2);

    await sharp(svgBuffer)
      .resize(iconSize, iconSize)
      .extend({
        top: offset,
        bottom: offset,
        left: offset,
        right: offset,
        background: { r: 9, g: 9, b: 11, alpha: 1 }, // #09090b
      })
      .png()
      .toFile(outputPath);
  } else {
    await sharp(svgBuffer).resize(size, size).png().toFile(outputPath);
  }

  console.log(`✓ Generated ${file} (${size}x${size}${maskable ? " maskable" : ""})`);
}

console.log("\nAll icons generated. Copy favicon-32.png → public/favicon.ico if needed.");
