import React, { useState } from "react";
import {
  ExtractionRecord,
  ExtractedFields,
  Product,
  Category,
  Severity,
  RequestedAction,
} from "../types";
import {
  AlertTriangle,
  CheckCircle,
  Save,
  Check,
  AlertCircle,
  XCircle,
} from "lucide-react";

interface ResultCardProps {
  record: ExtractionRecord;
  onSave: (recordId: string, patch: Partial<ExtractedFields>) => Promise<void>;
}

export const ResultCard: React.FC<ResultCardProps> = ({ record, onSave }) => {
  const extracted = record.extracted || {
    company: "",
    product: "Zen Connect" as Product,
    category: "bug" as Category,
    severity: "medium" as Severity,
    requested_action: "none" as RequestedAction,
    refund_amount: null,
    deadline: null,
    escalated: false,
  };

  // Local state for inline editing
  const [formData, setFormData] = useState<ExtractedFields>({
    company: extracted.company || "",
    product: extracted.product || "Zen Connect",
    category: extracted.category || "bug",
    severity: extracted.severity || "medium",
    requested_action: extracted.requested_action || "none",
    refund_amount: extracted.refund_amount,
    deadline: extracted.deadline || "",
    escalated: !!extracted.escalated,
  });

  const [dirtyFields, setDirtyFields] = useState<Set<keyof ExtractedFields>>(new Set());

  // Sync formData when record updates from save or polling
  React.useEffect(() => {
    if (record.extracted) {
      setFormData((prev) => ({
        company: record.extracted?.company ?? prev.company,
        product: record.extracted?.product ?? prev.product,
        category: record.extracted?.category ?? prev.category,
        severity: record.extracted?.severity ?? prev.severity,
        requested_action: record.extracted?.requested_action ?? prev.requested_action,
        refund_amount: record.extracted?.refund_amount ?? prev.refund_amount,
        deadline: record.extracted?.deadline ?? prev.deadline,
        escalated:
          record.extracted?.escalated !== undefined
            ? record.extracted.escalated
            : prev.escalated,
      }));
    }
  }, [record.extracted]);

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isNeedsReview = record.status === "needs_review";

  const handleFieldChange = (key: keyof ExtractedFields, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setDirtyFields((prev) => new Set(prev).add(key));
    setSavedSuccess(false);
    setErrorMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrorMessage(null);
    setSavedSuccess(false);

    try {
      const patch: Partial<ExtractedFields> = {};

      for (const key of Array.from(dirtyFields)) {
        const val = formData[key];
        if (key === "refund_amount") {
          patch.refund_amount =
            val === "" || val === null || val === undefined ? null : Number(val);
        } else if (key === "deadline") {
          patch.deadline =
            val === "" || val === null || val === undefined ? null : String(val);
        } else {
          (patch as any)[key] = val;
        }
      }


      if (Object.keys(patch).length === 0) {
        setSavedSuccess(true);
        setTimeout(() => setSavedSuccess(false), 3000);
        return;
      }

      await onSave(record.id, patch);
      setDirtyFields(new Set());
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };


 const renderProvenance = (fieldName: string) => {
  const isHuman = record.edited_fields?.includes(fieldName);
  const fieldValue = formData[fieldName as keyof ExtractedFields];

  if (isHuman) {
    return (
      <span className="text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded">
        Human edited
      </span>
    );
  }

  if (fieldValue === "" || fieldValue === null || fieldValue === undefined) {
    return (
      <span className="text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.5 rounded">
        Needs input
      </span>
    );
  }

  return (
    <span className="text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200 px-1.5 py-0.5 rounded">
      Model
    </span>
  );
};

  return (
    <div
      className={`bg-white rounded-xl shadow-sm overflow-hidden mb-6 transition-all border ${
        isNeedsReview
          ? "border-amber-400 ring-1 ring-amber-400 bg-amber-50/10"
          : "border-slate-200"
      }`}
    >
      {/* Top Header */}
      <div
        className={`px-6 py-3.5 flex flex-wrap items-center justify-between gap-3 border-b ${
          isNeedsReview
            ? "bg-amber-50/80 border-amber-200"
            : "bg-slate-50/70 border-slate-200"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-bold text-slate-900 bg-white border border-slate-200 px-2.5 py-0.5 rounded shadow-2xs">
            {record.ticket_id}
          </span>

          {/* Status Badge */}
          {isNeedsReview && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              NEEDS HUMAN REVIEW
            </span>
          )}

          {record.status === "done" && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle className="w-3.5 h-3.5" />
              Done
            </span>
          )}

          {record.status === "failed" && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
              <XCircle className="w-3.5 h-3.5" />
              Failed
            </span>
          )}

          {record.retry_count > 0 && (
            <span className="text-xs text-slate-500">
              (Retried: {record.retry_count})
            </span>
          )}
        </div>

        {/* Save / Status Controls */}
        <div className="flex items-center gap-3">
          {savedSuccess && (
            <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-semibold animate-fade-in">
              <Check className="w-3.5 h-3.5" /> Saved
            </span>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-2xs transition ${
              saving
                ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                : "bg-slate-900 hover:bg-slate-800 text-white cursor-pointer"
            }`}
          >
            <Save className="w-3.5 h-3.5" />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {/* Needs Review Explanation Banner */}
      {isNeedsReview && (
        <div className="px-6 py-3 bg-amber-50 border-b border-amber-200 text-xs text-amber-900">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-700 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-amber-950">
                Validation failed after retry. Please review and correct the fields on the right.
              </p>
              {record.validation_errors && record.validation_errors.length > 0 && (
                <ul className="list-disc list-inside mt-1 space-y-0.5 text-amber-800 font-mono text-[11px]">
                  {record.validation_errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error Alert Banner if Save failed */}
      {errorMessage && (
        <div className="px-6 py-3 bg-rose-50 border-b border-rose-200 text-xs text-rose-800 flex items-center gap-2">
          <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Split Review Grid */}
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT COLUMN: RAW TICKET */}
        <div className="flex flex-col h-full border-r-0 lg:border-r lg:border-slate-200 lg:pr-6">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
            Raw Customer Ticket
          </h4>

          {record.ticket ? (
            <div className="flex-1 flex flex-col">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-600 mb-3 space-y-1">
                <div>
                  <strong className="text-slate-800">Subject:</strong>{" "}
                  {record.ticket.subject || "(Empty)"}
                </div>
                <div>
                  <strong className="text-slate-800">From:</strong> {record.ticket.from_email}
                </div>
                <div className="flex gap-4">
                  <span>
                    <strong className="text-slate-800">Channel:</strong> {record.ticket.channel}
                  </span>
                  <span>
                    <strong className="text-slate-800">Date:</strong>{" "}
                    {new Date(record.ticket.received_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-4 font-mono text-xs text-slate-800 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[360px]">
                {record.ticket.body}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-lg">
              Raw ticket content not available.
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: EXTRACTED STRUCTURED FIELDS */}
        <div>
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
            Structured Extraction (Editable)
          </h4>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            {/* Company */}
            <div className="sm:col-span-2">
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Company Name *</label>
                {renderProvenance("company")}
              </div>
              <input
                type="text"
                value={formData.company}
                onChange={(e) => handleFieldChange("company", e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Required company name"
              />
            </div>

            {/* Product */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Product *</label>
                {renderProvenance("product")}
              </div>
              <select
                value={formData.product}
                onChange={(e) => handleFieldChange("product", e.target.value as Product)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="Zen Orchestrator">Zen Orchestrator</option>
                <option value="Zen Studio">Zen Studio</option>
                <option value="Zen Connect">Zen Connect</option>
                <option value="Zen Insights">Zen Insights</option>
                <option value="Zen Vault">Zen Vault</option>
              </select>
            </div>

            {/* Category */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Category *</label>
                {renderProvenance("category")}
              </div>
              <select
                value={formData.category}
                onChange={(e) => handleFieldChange("category", e.target.value as Category)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="outage">outage</option>
                <option value="billing">billing</option>
                <option value="bug">bug</option>
                <option value="feature_request">feature_request</option>
                <option value="how_to">how_to</option>
                <option value="churn_risk">churn_risk</option>
              </select>
            </div>

            {/* Severity */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Severity *</label>
                {renderProvenance("severity")}
              </div>
              <select
                value={formData.severity}
                onChange={(e) => handleFieldChange("severity", e.target.value as Severity)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </div>

            {/* Requested Action */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Requested Action *</label>
                {renderProvenance("requested_action")}
              </div>
              <select
                value={formData.requested_action}
                onChange={(e) =>
                  handleFieldChange("requested_action", e.target.value as RequestedAction)
                }
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="refund">refund</option>
                <option value="credit">credit</option>
                <option value="fix">fix</option>
                <option value="callback">callback</option>
                <option value="information">information</option>
                <option value="none">none</option>
              </select>
            </div>

            {/* Refund Amount */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Refund Amount ($ USD)</label>
                {renderProvenance("refund_amount")}
              </div>
              <input
                type="number"
                min="0"
                step="0.01"
                value={formData.refund_amount ?? ""}
                onChange={(e) =>
                  handleFieldChange(
                    "refund_amount",
                    e.target.value === "" ? null : parseFloat(e.target.value)
                  )
                }
                placeholder="Optional, e.g. 4820"
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Deadline */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-semibold text-slate-700">Deadline (YYYY-MM-DD)</label>
                {renderProvenance("deadline")}
              </div>
              <input
                type="date"
                value={formData.deadline || ""}
                onChange={(e) =>
                  handleFieldChange("deadline", e.target.value ? e.target.value : null)
                }
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Escalated Toggle */}
            <div className="sm:col-span-2 pt-2 border-t border-slate-100 flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={formData.escalated}
                  onChange={(e) => handleFieldChange("escalated", e.target.checked)}
                  className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                />
                Ticket is Escalated
              </label>
              {renderProvenance("escalated")}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
