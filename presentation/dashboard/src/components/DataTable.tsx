"use client";

import React from "react";
import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";

export interface Column<T> {
  header: string;
  accessor?: keyof T | ((item: T) => React.ReactNode);
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyText?: string;
  emptySubtext?: string;
  total?: number;
  limit?: number;
  offset?: number;
  onPageChange?: (newOffset: number) => void;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  loading = false,
  emptyText = "No data found",
  emptySubtext = "Scan repositories or adjust filters to view results",
  total = 0,
  limit = 20,
  offset = 0,
  onPageChange,
}: DataTableProps<T>) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="glass-card rounded-2xl border border-white/[0.06] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-[#090d17]/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-white/[0.06]">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={`px-6 py-4 ${col.className || ""}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {loading ? (
              Array.from({ length: 4 }).map((_, rIdx) => (
                <tr key={rIdx} className="animate-pulse">
                  {columns.map((_, cIdx) => (
                    <td key={cIdx} className="px-6 py-4">
                      <div className="h-3.5 bg-slate-800/60 rounded-md w-3/4"></div>
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center justify-center text-slate-400">
                    <div className="p-3.5 bg-white/[0.03] rounded-2xl border border-white/[0.08] mb-3 text-slate-400 shadow-inner">
                      <Inbox className="w-6 h-6" />
                    </div>
                    <p className="font-bold text-sm text-slate-200">{emptyText}</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm">{emptySubtext}</p>
                  </div>
                </td>
              </tr>
            ) : (
              data.map((item, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="hover:bg-white/[0.02] transition-colors border-b border-white/[0.03] last:border-0 group"
                >
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`px-6 py-4 font-medium text-slate-200 ${col.className || ""}`}>
                      {typeof col.accessor === "function"
                        ? col.accessor(item)
                        : col.accessor
                        ? item[col.accessor]
                        : null}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {onPageChange && total > 0 && (
        <div className="px-6 py-3.5 bg-[#080c16]/80 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="font-bold text-slate-200">{offset + 1}</span> to{" "}
            <span className="font-bold text-slate-200">{Math.min(offset + limit, total)}</span> of{" "}
            <span className="font-bold text-slate-200">{total}</span> items
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={offset === 0}
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.05] disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-slate-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={offset + limit >= total}
              onClick={() => onPageChange(offset + limit)}
              className="p-1.5 rounded-lg border border-white/[0.08] hover:bg-white/[0.05] disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
