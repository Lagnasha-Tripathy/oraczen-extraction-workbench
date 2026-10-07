"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Job, ExtractionRecord, ExtractedFields } from "../../../types";
import { getJob, getJobResults, patchRecord } from "../../../lib/api";
import { ProgressBar } from "../../../components/ProgressBar";
import { ResultCard } from "../../../components/ResultCard";
import { ArrowLeft, AlertCircle, RefreshCw } from "lucide-react";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<ExtractionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Poll function to fetch job progress and incremental results
  const pollJobData = async () => {
    if (!jobId) return;

    try {
      const [updatedJob, updatedResults] = await Promise.all([
        getJob(jobId),
        getJobResults(jobId),
      ]);

      setJob(updatedJob);
      setResults(updatedResults);
      setError(null);

      // Stop polling when job is completed or reached 100%
      if (updatedJob.status === "completed" || updatedJob.progress_percent >= 100) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load job data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    pollJobData();

    // Setup 1000ms polling interval
    pollIntervalRef.current = setInterval(() => {
      pollJobData();
    }, 1000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [jobId]);

  // Handle saving human corrections for a record
  const handleSaveRecord = async (
    recordId: string,
    patch: Partial<ExtractedFields>
  ) => {
    const updatedRecord = await patchRecord(recordId, patch);

    // Update the record in local state
    setResults((prev) =>
      prev.map((r) => (r.id === updatedRecord.id ? { ...r, ...updatedRecord } : r))
    );
  };

  // Sort results: "needs_review" records strictly float to the top
  const sortedResults = [...results].sort((a, b) => {
    if (a.status === "needs_review" && b.status !== "needs_review") return -1;
    if (a.status !== "needs_review" && b.status === "needs_review") return 1;
    return a.ticket_id.localeCompare(b.ticket_id);
  });

  if (loading && !job) {
    return (
      <div className="py-20 text-center">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-4" />
        <p className="text-slate-500 text-sm">Loading extraction job...</p>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="py-12 max-w-lg mx-auto text-center">
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm mb-4">
          <AlertCircle className="w-5 h-5 mx-auto mb-2 text-rose-600" />
          <p>{error}</p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-indigo-600 font-semibold hover:underline"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Tickets
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Back Button */}
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Inbox
        </Link>
      </div>

      {/* Progress Header */}
      {job && <ProgressBar job={job} hasResults={results.length > 0} />}

      {/* Results Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">
            Extracted Records ({results.length} of {job?.total || 0})
          </h3>
          <p className="text-xs text-slate-500">
            Review model extractions side-by-side with raw customer tickets. Items needing review are prioritized first.
          </p>
        </div>
      </div>

      {/* Results List */}
      {results.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500">
          <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin mx-auto mb-2" />
          <p className="text-sm font-medium">Processing tickets in background...</p>
          <p className="text-xs text-slate-400 mt-1">
            Results will appear automatically as each ticket finishes extraction.
          </p>
        </div>
      ) : (
        <div>
          {sortedResults.map((record) => (
            <ResultCard
              key={record.id}
              record={record}
              onSave={handleSaveRecord}
            />
          ))}
        </div>
      )}
    </div>
  );
}
