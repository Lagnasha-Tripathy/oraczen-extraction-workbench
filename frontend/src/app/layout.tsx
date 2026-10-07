import "./globals.css";
import React from "react";
import Link from "next/link";
import { Layers } from "lucide-react";

export const metadata = {
  title: "Oraczen Extraction Workbench",
  description: "Human-in-the-loop support ticket extraction and review",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {/* Navigation Bar */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 text-slate-900 hover:opacity-85 transition">
              <div className="bg-indigo-600 text-white p-2 rounded-lg">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <span className="font-bold text-base tracking-tight block">Oraczen</span>
                <span className="text-[10px] text-slate-500 font-medium tracking-wide uppercase block -mt-1">
                  Extraction Workbench
                </span>
              </div>
            </Link>

            <nav className="flex items-center gap-4 text-sm font-medium text-slate-600">
              <Link href="/" className="hover:text-indigo-600 transition">
                All Tickets
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content Container */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
