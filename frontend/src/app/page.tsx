"use client";

import { useState, useMemo, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { createCampaign } from "@/lib/api";
import { Send, Upload, CheckCircle2, AlertCircle, Sparkles, Building, Layers, Mail } from "lucide-react";

const BUSINESS_TYPES = [
  { value: "restaurant", label: "Restaurant" },
  { value: "real estate", label: "Real estate" },
  { value: "clinic or hospital", label: "Clinic or hospital" },
  { value: "online store", label: "Online store" },
  { value: "school or academy", label: "School or academy" },
  { value: "other business", label: "Other business" },
];

const SERVICES = [
  { value: "web design", label: "Web design" },
  { value: "SEO", label: "SEO" },
  { value: "website redesign", label: "Website redesign" },
];

const EMAIL_REGEX = /[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g;

export default function SendPage() {
  const router = useRouter();

  const [businessType, setBusinessType] = useState("restaurant");
  const [service, setService] = useState("web design");
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [successInfo, setSuccessInfo] = useState<{ id: number; total: number; unsubscribed: number } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Extract and deduplicate valid emails in real-time
  const parsedEmails = useMemo(() => {
    if (!rawText.trim()) return [];
    const matches = rawText.match(EMAIL_REGEX) || [];
    const unique = Array.from(new Set(matches.map((e) => e.toLowerCase().trim())));
    return unique;
  }, [rawText]);

  // Handle CSV/TXT file upload
  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setRawText((prev) => (prev ? `${prev}\n${content}` : content));
      }
    };
    reader.readAsText(file);
    e.target.value = ""; // Reset input
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessInfo(null);

    if (parsedEmails.length === 0) {
      setErrorMessage("Please enter or upload at least one valid email address.");
      return;
    }

    try {
      setLoading(true);
      const result = await createCampaign({
        business_type: businessType,
        service: service,
        email_addresses: parsedEmails,
      });

      setSuccessInfo({
        id: result.id,
        total: result.total_emails,
        unsubscribed: result.unsubscribed_count,
      });
      setRawText("");
    } catch (err: any) {
      setErrorMessage(
        err.message || "Failed to start sending campaign. Please check backend server."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Intro Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Send cold emails</h1>
        <p className="text-sm text-slate-500 mt-1">
          Select target industry and service, paste your recipient list, and click start. Gemini AI writes each message, Python validates quality, and the background worker sends each email automatically.
        </p>
      </div>

      {/* Success Notification */}
      {successInfo && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-in fade-in">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-semibold text-sm">Batch #{successInfo.id} created successfully</p>
              <p className="text-xs text-emerald-700">
                {successInfo.total - successInfo.unsubscribed} emails queued.
                {successInfo.unsubscribed > 0 && ` ${successInfo.unsubscribed} unsubscribed address(es) skipped.`}
                {successInfo.total > successInfo.unsubscribed
                  ? " Sending has begun automatically in the background."
                  : " No emails were queued because all recipients have opted out."}
              </p>
            </div>
          </div>
          <button
            onClick={() => router.push("/report")}
            className="px-3.5 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 transition-colors shadow-sm shrink-0"
          >
            View live report &rarr;
          </button>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">Unable to start campaign</p>
            <p className="text-red-700 text-xs">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Main Form Card */}
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Dropdown 1: Business Type */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Building className="w-4 h-4 text-slate-500" />
              Business type
            </label>
            <select
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all shadow-sm"
            >
              {BUSINESS_TYPES.map((bt) => (
                <option key={bt.value} value={bt.value}>
                  {bt.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-400">
              AI addresses industry pain points specific to this business.
            </p>
          </div>

          {/* Dropdown 2: Service */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Layers className="w-4 h-4 text-slate-500" />
              Our service
            </label>
            <select
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all shadow-sm"
            >
              {SERVICES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-slate-400">
              Subject line and pitch text will strictly match this service.
            </p>
          </div>
        </div>

        {/* Email Addresses Textarea & File Upload */}
        <div className="space-y-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Mail className="w-4 h-4 text-slate-500" />
              Email addresses
            </label>

            <div className="flex items-center gap-3">
              {/* File upload button */}
              <label className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1.5 rounded-lg transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span>Upload CSV / TXT</span>
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>

              {/* Dynamic Count of Valid Addresses Found */}
              <span
                className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                  parsedEmails.length > 0
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {parsedEmails.length} valid {parsedEmails.length === 1 ? "address" : "addresses"} found
              </span>
            </div>
          </div>

          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={7}
            placeholder="Paste any number of email addresses here (separated by commas, spaces, or new lines) or upload a CSV/TXT file..."
            className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3.5 text-sm text-slate-800 font-mono placeholder:font-sans placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all shadow-sm resize-y"
          />

          <p className="text-xs text-slate-400">
            Duplicates and invalid emails are filtered automatically. Unsubscribed addresses are never queued.
          </p>
        </div>

        {/* Start Sending Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={loading || parsedEmails.length === 0}
            className={`w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold text-white transition-all shadow-sm ${
              loading || parsedEmails.length === 0
                ? "bg-slate-300 cursor-not-allowed text-slate-500"
                : "bg-blue-600 hover:bg-blue-700 active:scale-[0.99] shadow-blue-500/20"
            }`}
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Creating campaign...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>
                  Start sending {parsedEmails.length > 0 ? `(${parsedEmails.length} emails)` : ""}
                </span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
