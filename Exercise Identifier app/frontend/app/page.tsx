export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-md text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Exercise Identifier
        </h1>
        <p className="mt-4 text-neutral-400">
          Frontend infrastructure is live. Next up: wire the API.
        </p>
        <div className="mt-8 rounded-xl border border-neutral-800 bg-neutral-900 p-4 text-left text-sm">
          <p className="text-neutral-500">Backend target</p>
          <p className="font-mono text-neutral-200">
            http://localhost:8000
          </p>
        </div>
      </div>
    </main>
  );
}
