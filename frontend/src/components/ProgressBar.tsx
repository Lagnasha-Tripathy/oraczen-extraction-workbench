import React from "react";
import { Job } from "../types";
import { getExportUrl } from "../lib/api";
import { Download, CheckCircle, AlertTriangle, XCircle, Clock, Loader2 } from "lucide-react";

interface ProgressBarProps {
  job: Job;
  hasResults: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ job, hasResults }) => {
  const isFinished = job.status === "completed" || job.progress_percent >= 100;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm mb-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-slate-900">Job: {job.id}</h2>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                job.status === "completed"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : job.status === "running"
                  ? "bg-blue-50 text-blue-700 border border-blue-200 animate-pulse"
                  : "bg-slate-100 text-slate-700 border border-slate-200"
              }`}
            >
              {job.status === "running" && <Loader2 className="w-3 h-3 animate-spin" />}
              {job.status === "completed" && <CheckCircle className="w-3 h-3" />}
              {job.status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isFinished
              ? "All tickets processed and ready for review."
              : "Extracting ticket fields in the background..."}
          </p>
        </div>

        {/* CSV Export Button */}
        <div>
          <a
            href={getExportUrl(job.id)}
            download
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition shadow-sm ${
              hasResults
                ? "bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer"
                : "bg-slate-100 text-slate-400 cursor-not-allowed pointer-events-none"
            }`}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </a>
        </div>
      </div>

      {/* Progress Bar Track */}
      <div className="w-full bg-slate-100 rounded-full h-3 mb-4 overflow-hidden border border-slate-200">
        <div
          className={`h-full transition-all duration-300 rounded-full ${
            job.status === "completed" ? "bg-emerald-500" : "bg-indigo-600"
          }`}
          style={{ width: `${Math.min(100, job.progress_percent)}%` }}
        />
      </div>

      {/* Metric Counters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 pt-2 border-t border-slate-100 text-center">
        <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
          <div className="text-xs text-slate-500 font-medium">Progress</div>
          <div className="text-lg font-bold text-slate-800">{job.progress_percent}%</div>
        </div>

        <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
          <div className="text-xs text-slate-500 font-medium">Total</div>
          <div className="text-lg font-bold text-slate-800">{job.total}</div>
        </div>

        <div className="bg-blue-50/50 p-2.5 rounded-lg border border-blue-100">
          <div className="text-xs text-blue-600 font-medium flex items-center justify-center gap-1">
            <Clock className="w-3 h-3" /> Running
          </div>
          <div className="text-lg font-bold text-blue-700">{job.running}</div>
        </div>

        <div className="bg-emerald-50/50 p-2.5 rounded-lg border border-emerald-100">
          <div className="text-xs text-emerald-600 font-medium flex items-center justify-center gap-1">
            <CheckCircle className="w-3 h-3" /> Completed
          </div>
          <div className="text-lg font-bold text-emerald-700">{job.completed}</div>
        </div>

        <div className="bg-amber-50/50 p-2.5 rounded-lg border border-amber-100">
          <div className="text-xs text-amber-600 font-medium flex items-center justify-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Needs Review
          </div>
          <div className="text-lg font-bold text-amber-700">{job.needs_review}</div>
        </div>

        <div className="bg-rose-50/50 p-2.5 rounded-lg border border-rose-100">
          <div className="text-xs text-rose-600 font-medium flex items-center justify-center gap-1">
            <XCircle className="w-3 h-3" /> Failed
          </div>
          <div className="text-lg font-bold text-rose-700">{job.failed}</div>
        </div>
      </div>
    </div>
  );
};
