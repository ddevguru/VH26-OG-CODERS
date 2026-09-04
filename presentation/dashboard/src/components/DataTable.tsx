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
    <div className="glass-card rounded-xl border border-gray-800/80 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-[#0b0f17]/90 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-800/80">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={`px-5 py-3.5 ${col.className || ""}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60">
            {loading ? (
              Array.from({ length: 5 }).map((_, rIdx) => (
                <tr key={rIdx} className="animate-pulse">
                  {columns.map((_, cIdx) => (
                    <td key={cIdx} className="px-5 py-4">
                      <div className="h-4 bg-gray-800/80 rounded w-3/4"></div>
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-5 py-12 text-center">
                  <div className="flex flex-col items-center justify-center text-gray-400">
                    <div className="p-3 bg-gray-800/50 rounded-full border border-gray-700/50 mb-3 text-gray-400">
                      <Inbox className="w-8 h-8" />
                    </div>
                    <p className="font-semibold text-base text-gray-200">{emptyText}</p>
                    <p className="text-xs text-gray-400 mt-1 max-w-sm">{emptySubtext}</p>
                  </div>
                </td>
              </tr>
            ) : (
              data.map((item, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="hover:bg-gray-800/30 transition-colors border-b border-gray-800/40 last:border-0"
                >
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`px-5 py-4 ${col.className || ""}`}>
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
        <div className="px-5 py-3.5 bg-[#0b0f17]/80 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
          <div>
            Showing <span className="font-semibold text-gray-200">{offset + 1}</span> to{" "}
            <span className="font-semibold text-gray-200">{Math.min(offset + limit, total)}</span> of{" "}
            <span className="font-semibold text-gray-200">{total}</span> items
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={offset === 0}
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              className="p-1.5 rounded-lg border border-gray-800 hover:bg-gray-800 disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-gray-300">
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={offset + limit >= total}
              onClick={() => onPageChange(offset + limit)}
              className="p-1.5 rounded-lg border border-gray-800 hover:bg-gray-800 disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
