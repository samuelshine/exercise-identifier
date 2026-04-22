# Frontend — Exercise Identifier

Next.js 14 (App Router) + Tailwind CSS + TypeScript. Mobile-first PWA shell.

## Setup

```bash
cd frontend
npm install
```

## Run (dev)

```bash
npm run dev
```

Opens at http://localhost:3000. The page is a placeholder that confirms the
Tailwind build is working and points at the local FastAPI backend on
`http://localhost:8000`.

## Layout

```
frontend/
├── app/
│   ├── globals.css      # Tailwind directives + base styles
│   ├── layout.tsx       # Root layout, mobile viewport, PWA meta
│   └── page.tsx         # Placeholder landing page
├── next.config.mjs
├── tailwind.config.ts
├── postcss.config.mjs
├── tsconfig.json
└── package.json
```
