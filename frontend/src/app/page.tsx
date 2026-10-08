"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Ticket } from "../types";
import { fetchTickets, createJob } from "../lib/api";
import { TicketList } from "../components/TicketList";
import { AlertCircle } from "lucide-react";

export default function HomePage() {
  const router = useRouter();

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadSeconds, setLoadSeconds] = useState(0);

  const [search, setSearch] = useState("");
  const [channel, setChannel] = useState("all");
  const [isLaunching, setIsLaunching] = useState(false);

  // Count elapsed seconds while loading so we can show a helpful message
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startTimer = () => {
    setLoadSeconds(0);
    timerRef.current = setInterval(() => {
      setLoadSeconds((s) => s + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // Fetch tickets from backend
  const loadTickets = async () => {
    setLoading(true);
    setError(null);
    startTimer();
    try {
      const data = await fetchTickets({
        search: search.trim() || undefined,
        channel: channel !== "all" ? channel : undefined,
        limit: 150,
      });
      setTickets(data.tickets);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load tickets from backend");
    } finally {
      setLoading(false);
      stopTimer();
    }
  };

  useEffect(() => {
    loadTickets();
    return () => stopTimer();
  }, [search, channel]);

  // Handle launch extraction job
  const handleLaunch = async (selectedIds: string[]) => {
    if (selectedIds.length === 0) return;
    setIsLaunching(true);
    setError(null);
    try {
      const job = await createJob(selectedIds);
      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to launch extraction job");
      setIsLaunching(false);
    }
  };

  // Show waking-up hint after 3 seconds of loading
  const showWakeUpHint = loading && loadSeconds >= 3;

  return (
    <div>
      {/* Page Title & Intro */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Support Inbox Tickets
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Select raw customer support tickets to run AI-assisted structured
          extraction and human-in-the-loop review.
        </p>
      </div>

      {/* Wake-up hint — shown after 3 seconds of loading */}
      {showWakeUpHint && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-sm">
          <p className="font-semibold mb-1">
            ⏳ Backend is waking up… ({loadSeconds}s)
          </p>
          <p className="text-amber-700">
            The server starts up automatically on first visit. This takes about
            30–50 seconds on the free tier. The tickets will load on their own —
            no need to refresh.
          </p>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
          <span>{error}</span>
          <button
            onClick={loadTickets}
            className="ml-auto px-3 py-1 bg-rose-600 text-white rounded-lg text-xs hover:bg-rose-700"
          >
            Retry
          </button>
        </div>
      )}

      {/* Ticket Selection List Component */}
      <TicketList
        tickets={tickets}
        total={total}
        loading={loading}
        onLaunch={handleLaunch}
        isLaunching={isLaunching}
        search={search}
        onSearchChange={setSearch}
        channel={channel}
        onChannelChange={setChannel}
      />
    </div>
  );
}
