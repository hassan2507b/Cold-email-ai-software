"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchStats,
  fetchCampaigns,
  fetchLatestEmails,
  retryProblemEmails,
  ReportStats,
  Campaign,
  EmailRecord,
} from "@/lib/api";
import { EmailModal } from "@/components/EmailModal";
import {
  RotateCcw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldAlert,
  Calendar,
  Layers,
  ChevronRight,
  Info,
} from "lucide-react";

export default function ReportPage() {
  const [stats, setStats] = useState<ReportStats | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [latestEmails, setLatestEmails] = useState<EmailRecord[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailRecord | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setLastRefreshed(new Date());
  }, []);

  const loadData = useCallback(async () => {
    try {
      const [s, c, l] = await Promise.all([
        fetchStats(),
        fetchCampaigns(),
        fetchLatestEmails(20),
      ]);
      setStats(s);
      setCampaigns(c);
      setLatestEmails(l);
      setLastRefreshed(new Date());
      setLoadError(null);
    } catch (err) {
      console.error("Auto refresh error:", err);
      setLoadError(err instanceof Error ? err.message : "Could not load report data.");
    }
  }, []);

  // Auto-refresh interval (every 3 seconds)
  useEffect(() => {
    loadData();
    const timer = setInterval(() => {
      loadData();
    }, 3000);
    return () => clearInterval(timer);
  }, [loadData]);

  const handleRetryAll = async () => {
    try {
      setRetrying(true);
      setRetryMessage(null);
      const res = await retryProblemEmails();
      setRetryMessage(res.message);
      await loadData();
      setTimeout(() => setRetryMessage(null), 5000);
    } catch (err: any) {
      setRetryMessage(err.message || "Failed to retry problem emails.");
    } finally {
      setRetrying(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "sent":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3" />
            Sent
          </span>
        );
      case "waiting":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3" />
            Waiting
          </span>
        );
      case "sending":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
            <Clock className="w-3 h-3" />
            Sending
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
            <AlertTriangle className="w-3 h-3" />
            Not sent
          </span>
        );
      case "blocked by checks":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            <ShieldAlert className="w-3 h-3" />
            Blocked by checks
          </span>
        );
      case "unsubscribed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            Unsubscribed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Bar with Title, Auto-refresh indicator, and Retry Button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Campaign report</h1>
          <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
            <span>Refreshes automatically every 3 seconds</span>
            <span>&bull;</span>
            <span suppressHydrationWarning>
              {mounted && lastRefreshed ? `Last updated ${lastRefreshed.toLocaleTimeString()}` : "Live dashboard"}
            </span>
          </div>
        </div>

        <div>
          <button
            onClick={handleRetryAll}
            disabled={retrying}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-sm transition-all disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${retrying ? "animate-spin text-blue-600" : "text-slate-500"}`} />
            <span>{retrying ? "Retrying..." : "Retry all problems"}</span>
          </button>
        </div>
      </div>

      {loadError && (
        <div role="alert" className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
          Could not refresh report data: {loadError}
        </div>
      )}

      {/* Retry Message Alert */}
      {retryMessage && (
        <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-sm flex items-center gap-2 animate-in fade-in">
          <Info className="w-4 h-4 text-blue-600 shrink-0" />
          <span>{retryMessage}</span>
        </div>
      )}

      {/* Counters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Sent */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Sent</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold text-slate-900">{stats?.sent ?? 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Delivered via SMTP</span>
          </div>
        </div>

        {/* Waiting */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Waiting</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold text-slate-900">{stats?.waiting ?? 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">In sending queue</span>
          </div>
        </div>

        {/* Not sent */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Not sent</span>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold text-slate-900">{stats?.not_sent ?? 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">SMTP or network errors</span>
          </div>
        </div>

        {/* Blocked by checks */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Blocked by checks</span>
            <ShieldAlert className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold text-slate-900">{stats?.blocked_by_checks ?? 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Failed Python checks</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Unsubscribed</span>
            <ShieldAlert className="w-4 h-4 text-slate-500" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold text-slate-900">{stats?.unsubscribed ?? 0}</span>
            <span className="text-xs text-slate-400 block mt-0.5">Suppressed from future sends</span>
          </div>
        </div>

        {/* Sent in the last 24 hours */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Sent in the last 24 hours</span>
            <Calendar className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl sm:text-3xl font-bold text-slate-900">
                {stats?.sent_last_24h ?? 0}
              </span>
              <span className="text-xs text-slate-400">/ {stats?.daily_limit ?? 400}</span>
            </div>
            <span className="text-xs text-slate-400 block mt-0.5">
              Rolling limit {stats?.daily_limit ?? 400}
            </span>
          </div>
        </div>
      </div>

      {/* Table 1: Batches with Progress */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-500" />
            <h2 className="text-base font-semibold text-slate-900">Batches</h2>
          </div>
          <span className="text-xs text-slate-400">{campaigns.length} batch(es)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-6 py-3 font-semibold">Batch id</th>
                <th className="px-6 py-3 font-semibold">Business type</th>
                <th className="px-6 py-3 font-semibold">Service</th>
                <th className="px-6 py-3 font-semibold">Total</th>
                <th className="px-6 py-3 font-semibold">Progress</th>
                <th className="px-6 py-3 font-semibold text-right">Created time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                    No batches created yet. Go to Send emails to start sending.
                  </td>
                </tr>
              ) : (
                campaigns.map((batch) => (
                  <tr key={batch.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-900">#{batch.id}</td>
                    <td className="px-6 py-4 capitalize text-slate-700">{batch.business_type}</td>
                    <td className="px-6 py-4 capitalize text-slate-700">{batch.service}</td>
                    <td className="px-6 py-4 font-medium text-slate-900">{batch.total_emails}</td>
                    <td className="px-6 py-4 min-w-[200px]">
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-slate-700">
                            {batch.sent_count} / {batch.total_emails} sent
                          </span>
                          <span className="text-slate-400">{batch.progress_percentage}%</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden flex">
                          <div
                            className="bg-emerald-500 h-full transition-all duration-300"
                            style={{
                              width: `${(batch.sent_count / batch.total_emails) * 100}%`,
                            }}
                          />
                          <div
                            className="bg-amber-400 h-full transition-all duration-300"
                            style={{
                              width: `${(batch.waiting_count / batch.total_emails) * 100}%`,
                            }}
                          />
                          <div
                            className="bg-blue-400 h-full transition-all duration-300"
                            style={{
                              width: `${(batch.sending_count / batch.total_emails) * 100}%`,
                            }}
                          />
                          <div
                            className="bg-red-400 h-full transition-all duration-300"
                            style={{
                              width: `${((batch.failed_count + batch.blocked_count) / batch.total_emails) * 100}%`,
                            }}
                          />
                          <div
                            className="bg-slate-300 h-full transition-all duration-300"
                            style={{
                              width: `${(batch.unsubscribed_count / batch.total_emails) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td suppressHydrationWarning className="px-6 py-4 text-xs text-slate-400 text-right">
                      {mounted ? new Date(batch.created_time).toLocaleString() : ""}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Table 2: Latest Emails with Status & Reason */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Latest emails</h2>
            <p className="text-xs text-slate-400">
              Showing the most recent 20 emails. Click any row to preview full email body and error diagnostics.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-6 py-3 font-semibold">Recipient</th>
                <th className="px-6 py-3 font-semibold">Service</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold">Reason</th>
                <th className="px-6 py-3 font-semibold text-right">Created time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {latestEmails.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    No emails in history yet.
                  </td>
                </tr>
              ) : (
                latestEmails.map((email) => (
                  <tr
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900">{email.recipient}</div>
                      <div className="text-xs text-slate-400 capitalize">{email.business_type}</div>
                    </td>
                    <td className="px-6 py-4 capitalize text-slate-700">{email.service}</td>
                    <td className="px-6 py-4">{getStatusBadge(email.status)}</td>
                    <td className="px-6 py-4 max-w-xs truncate text-xs text-slate-500">
                      {email.error_reason ? (
                        <span className="text-red-600 font-mono text-xs">{email.error_reason}</span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td suppressHydrationWarning className="px-6 py-4 text-xs text-slate-400 text-right whitespace-nowrap">
                      {mounted ? new Date(email.created_time).toLocaleTimeString() : ""}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal for Email Details */}
      <EmailModal email={selectedEmail} onClose={() => setSelectedEmail(null)} />
    </div>
  );
}
