import React, { useState } from "react";
import { Ticket } from "../types";
import { Search, Filter, Play, CheckSquare, Square } from "lucide-react";

interface TicketListProps {
  tickets: Ticket[];
  total: number;
  loading: boolean;
  onLaunch: (selectedIds: string[]) => void;
  isLaunching: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  channel: string;
  onChannelChange: (value: string) => void;
}

export const TicketList: React.FC<TicketListProps> = ({
  tickets,
  total,
  loading,
  onLaunch,
  isLaunching,
  search,
  onSearchChange,
  channel,
  onChannelChange,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Toggle single ticket
  const toggleTicket = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  // Select all visible
  const selectAll = () => {
    const next = new Set(selectedIds);
    tickets.forEach((t) => next.add(t.id));
    setSelectedIds(next);
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  const isAllSelected = tickets.length > 0 && tickets.every((t) => selectedIds.has(t.id));

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Top Filter and Action Bar */}
      <div className="p-4 sm:p-6 border-b border-slate-200 bg-slate-50/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Search Input */}
          <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search by ticket ID, subject, text, or sender..."
                value={search}
                onChange={(e) => onSearchChange(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-900 placeholder:text-slate-400"
              />
            </div>

            {/* Channel Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={channel}
                onChange={(e) => onChannelChange(e.target.value)}
                className="py-2 px-3 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-slate-700"
              >
                <option value="all">All Channels</option>
                <option value="email">Email</option>
                <option value="web_form">Web Form</option>
                <option value="chat">Chat</option>
                <option value="phone_transcript">Phone Transcript</option>
              </select>
            </div>
          </div>

          {/* Action Button */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-medium">
              {selectedIds.size} of {total} selected
            </span>
            <button
              onClick={() => onLaunch(Array.from(selectedIds))}
              disabled={selectedIds.size === 0 || isLaunching}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition shadow-sm ${
                selectedIds.size > 0 && !isLaunching
                  ? "bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed"
              }`}
            >
              <Play className="w-4 h-4 fill-current" />
              {isLaunching ? "Starting Job..." : `Launch Extraction (${selectedIds.size})`}
            </button>
          </div>
        </div>

        {/* Bulk Selection Controls */}
        <div className="flex items-center gap-4 mt-4 pt-3 border-t border-slate-200 text-xs text-slate-600">
          <button
            onClick={isAllSelected ? clearSelection : selectAll}
            className="hover:text-indigo-600 font-medium inline-flex items-center gap-1.5 transition"
          >
            {isAllSelected ? (
              <>
                <CheckSquare className="w-3.5 h-3.5 text-indigo-600" /> Deselect All
              </>
            ) : (
              <>
                <Square className="w-3.5 h-3.5" /> Select All Visible ({tickets.length})
              </>
            )}
          </button>
          {selectedIds.size > 0 && (
            <button onClick={clearSelection} className="hover:text-red-600 transition">
              Clear All Selection
            </button>
          )}
        </div>
      </div>

      {/* Ticket Rows */}
      {loading ? (
        <div className="p-12 text-center text-slate-500">Loading tickets...</div>
      ) : tickets.length === 0 ? (
        <div className="p-12 text-center text-slate-500">
          No tickets found matching your filter criteria.
        </div>
      ) : (
        <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
          {tickets.map((t) => {
            const isSelected = selectedIds.has(t.id);
            return (
              <div
                key={t.id}
                onClick={() => toggleTicket(t.id)}
                className={`p-4 flex items-start gap-3 hover:bg-slate-50 cursor-pointer transition ${
                  isSelected ? "bg-indigo-50/40" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => {}} // handled by row click
                  className="mt-1 w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                        {t.id}
                      </span>
                      <h4 className="text-sm font-semibold text-slate-900 truncate">
                        {t.subject || "(No Subject)"}
                      </h4>
                    </div>

                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600 border border-slate-200">
                      {t.channel}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {t.body}
                  </p>

                  <div className="flex items-center gap-4 mt-2 text-[11px] text-slate-400">
                    <span>From: {t.from_email}</span>
                    <span>Received: {new Date(t.received_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
