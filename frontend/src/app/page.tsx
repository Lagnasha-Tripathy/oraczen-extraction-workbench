"use client";

import React, { useEffect, useState } from "react";
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

  const [search, setSearch] = useState("");
  const [channel, setChannel] = useState("all");
  const [isLaunching, setIsLaunching] = useState(false);

  // Fetch tickets from backend
  const loadTickets = async () => {
    setLoading(true);
    setError(null);
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
    }
  };

  useEffect(() => {
    loadTickets();
  }, [search, channel]);

  // Handle launch extraction job
  const handleLaunch = async (selectedIds: string[]) => {
    if (selectedIds.length === 0) return;
    setIsLaunching(true);
    setError(null);

    try {
      const job = await createJob(selectedIds);
      // HTTP 202 received with job.id -> navigate to review workbench
      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to launch extraction job");
      setIsLaunching(false);
    }
  };

  return (
    <div>
      {/* Page Title & Intro */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Support Inbox Tickets
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Select raw customer support tickets to run AI-assisted structured extraction and human-in-the-loop review.
        </p>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-600" />
          <span>{error}</span>
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
