"use client";

import { EmailRecord } from "@/lib/api";
import { X, CheckCircle2, Clock, AlertTriangle, ShieldAlert, Copy, Check } from "lucide-react";
import { useState } from "react";

interface EmailModalProps {
  email: EmailRecord | null;
  onClose: () => void;
}

export function EmailModal({ email, onClose }: EmailModalProps) {
  const [copied, setCopied] = useState(false);

  if (!email) return null;

  const handleCopy = () => {
    if (email.body) {
      navigator.clipboard.writeText(email.body);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "sent":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Sent
          </span>
        );
      case "waiting":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3.5 h-3.5" />
            Waiting
          </span>
        );
      case "sending":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
            <Clock className="w-3.5 h-3.5" />
            Sending
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Not sent
          </span>
        );
      case "blocked by checks":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            <ShieldAlert className="w-3.5 h-3.5" />
            Blocked by checks
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-slate-900">Email details</h3>
            {getStatusBadge(email.status)}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm bg-slate-50 p-4 rounded-xl border border-slate-100">
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Recipient</span>
              <span className="font-medium text-slate-800 break-all">{email.recipient}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Subject</span>
              <span className="font-medium text-slate-800">{email.subject}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Business type</span>
              <span className="capitalize text-slate-700">{email.business_type}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Service</span>
              <span className="capitalize text-slate-700">{email.service}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Created time</span>
              <span suppressHydrationWarning className="text-slate-600">
                {new Date(email.created_time).toLocaleString()}
              </span>
            </div>
            <div>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block">Sent time</span>
              <span suppressHydrationWarning className="text-slate-600">
                {email.sent_time ? new Date(email.sent_time).toLocaleString() : "Not sent yet"}
              </span>
            </div>
          </div>

          {/* Error Details If Failed or Blocked */}
          {email.error_reason && (
            <div className="p-4 rounded-xl border border-red-200 bg-red-50 text-red-900 text-sm space-y-2">
              <div className="flex items-center gap-2 font-medium text-red-800">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>What went wrong</span>
              </div>
              <p className="text-red-700 font-mono text-xs bg-white/70 p-2.5 rounded-lg border border-red-100 whitespace-pre-wrap">
                {email.error_reason}
              </p>
              <div className="text-xs text-red-800 pt-1">
                <strong>How to fix it:</strong>{" "}
                {email.status === "unsubscribed"
                  ? "This address has opted out and will not be sent future campaign emails."
                  : email.status === "blocked by checks"
                  ? "The AI was unable to satisfy strict quality rules after 3 attempts. You can click 'Retry all problems' on the Report page to retry generation."
                  : "Verify your SMTP and Gemini credentials in backend/.env, check network connection, or click 'Retry all problems' on the Report page."}
              </div>
            </div>
          )}

          {/* Email Body */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Email message body
              </span>
              {email.body && (
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 transition-colors px-2 py-1 rounded hover:bg-slate-100"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copied" : "Copy text"}</span>
                </button>
              )}
            </div>

            {email.body ? (
              <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 text-sm text-slate-800 whitespace-pre-wrap font-sans leading-relaxed">
                {email.body}
              </div>
            ) : (
              <div className="bg-slate-50 p-6 rounded-xl border border-dashed border-slate-200 text-center text-sm text-slate-400">
                This email is still waiting in the queue. The AI model will write the email automatically when sending begins.
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
