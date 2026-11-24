"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchAllEmails, EmailRecord } from "@/lib/api";
import { EmailModal } from "@/components/EmailModal";
import {
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldAlert,
  Inbox,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const PAGE_SIZE = 50;

export default function SentEmailsPage() {
  const [emails, setEmails] = useState<EmailRecord[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const [selectedEmail, setSelectedEmail] = useState<EmailRecord | null>(null);

  const loadEmails = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchAllEmails(search, statusFilter, PAGE_SIZE, offset);
      setEmails(data.emails);
      setHasMore(data.hasMore);
      setLoadError(null);
    } catch (err) {
      console.error("Failed to load emails:", err);
      setLoadError(err instanceof Error ? err.message : "Failed to load emails.");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, offset]);

  useEffect(() => {
    const handler = setTimeout(() => {
      loadEmails();
    }, 250);
    return () => clearTimeout(handler);
  }, [loadEmails]);

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
    <div className="space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sent emails</h1>
        <p className="text-sm text-slate-500 mt-1">
          Complete archive of every recipient and email generated. Click on any row to view the full email copy that was written.
        </p>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            placeholder="Search by email address..."
            className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
          />
        </div>

        {/* Filter by Status & Refresh */}
        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
              className="bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all shadow-sm w-full sm:w-auto"
            >
              <option value="all">All statuses</option>
              <option value="sent">Sent</option>
              <option value="waiting">Waiting</option>
              <option value="failed">Not sent</option>
              <option value="blocked by checks">Blocked by checks</option>
              <option value="unsubscribed">Unsubscribed</option>
            </select>
          </div>

          <button
            onClick={loadEmails}
            title="Refresh list"
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
          </button>
        </div>
      </div>

      {loadError && (
        <div role="alert" className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
          {loadError}
        </div>
      )}

      {/* Emails Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-100">
              <tr>
                <th className="px-6 py-3 font-semibold">Recipient</th>
                <th className="px-6 py-3 font-semibold">Business type</th>
                <th className="px-6 py-3 font-semibold">Service</th>
                <th className="px-6 py-3 font-semibold">Subject</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading && emails.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    <div className="inline-block w-5 h-5 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin mb-2" />
                    <p>Loading emails...</p>
                  </td>
                </tr>
              ) : emails.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    <Inbox className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                    <p className="font-medium text-slate-600">No emails found</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {search || statusFilter !== "all"
                        ? "Try clearing your search query or status filter."
                        : "Send your first campaign from the Send emails page."}
                    </p>
                  </td>
                </tr>
              ) : (
                emails.map((email) => (
                  <tr
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">{email.recipient}</td>
                    <td className="px-6 py-4 capitalize text-slate-700">{email.business_type}</td>
                    <td className="px-6 py-4 capitalize text-slate-700">{email.service}</td>
                    <td className="px-6 py-4 text-slate-800">{email.subject}</td>
                    <td className="px-6 py-4">{getStatusBadge(email.status)}</td>
                    <td suppressHydrationWarning className="px-6 py-4 text-xs text-slate-400 text-right whitespace-nowrap">
                      {new Date(email.sent_time || email.created_time).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
          disabled={offset === 0 || loading}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 disabled:opacity-40"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>
        <span className="text-xs text-slate-500">
          {emails.length ? `${offset + 1}–${offset + emails.length}` : "No results"}
        </span>
        <button
          type="button"
          onClick={() => setOffset((current) => current + PAGE_SIZE)}
          disabled={!hasMore || loading}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 disabled:opacity-40"
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Modal for viewing the complete email text that was written */}
      <EmailModal email={selectedEmail} onClose={() => setSelectedEmail(null)} />
    </div>
  );
}
