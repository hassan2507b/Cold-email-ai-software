"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { AlertCircle, LockKeyhole, Mail } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      router.replace("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to log in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-10">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm bg-white rounded-2xl border border-slate-200 p-7 shadow-sm space-y-5"
      >
        <div>
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center mb-4">
            <Mail className="w-5 h-5" />
          </div>
          <h1 className="text-xl font-bold text-slate-900">Sign in to ColdMail AI</h1>
          <p className="text-sm text-slate-500 mt-1">Use the dashboard credentials from backend/.env.</p>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm flex gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-slate-700">Username</span>
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-slate-700">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          <LockKeyhole className="w-4 h-4" />
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
