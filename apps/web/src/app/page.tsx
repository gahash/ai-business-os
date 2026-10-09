"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  status: "healthy" | "degraded";
  services: Record<string, string>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`API responded ${res.status}`);
        return res.json();
      })
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 p-16 font-sans dark:bg-black">
      <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">AI Business OS</h1>
      <p className="text-zinc-600 dark:text-zinc-400">
        M1 — Infrastructure. Frontend talking to backend at{" "}
        <code className="rounded bg-black/[.06] px-1.5 py-0.5 font-mono text-sm dark:bg-white/[.08]">
          {API_URL}
        </code>
      </p>

      {error && (
        <div className="rounded border border-red-300 bg-red-50 px-4 py-3 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          Impossibile contattare il backend: {error}
        </div>
      )}

      {health && (
        <div className="w-full max-w-md rounded border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-3 flex items-center gap-2">
            <span
              className={`h-3 w-3 rounded-full ${
                health.status === "healthy" ? "bg-green-500" : "bg-yellow-500"
              }`}
            />
            <span className="font-medium text-black dark:text-zinc-50">
              {health.status}
            </span>
          </div>
          <ul className="space-y-1 text-sm">
            {Object.entries(health.services).map(([name, status]) => (
              <li key={name} className="flex justify-between font-mono">
                <span className="text-zinc-500 dark:text-zinc-400">{name}</span>
                <span className="text-black dark:text-zinc-50">{status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
