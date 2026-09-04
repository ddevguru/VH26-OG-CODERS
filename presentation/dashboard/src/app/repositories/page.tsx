"use client";

import React, { useEffect, useState } from "react";
import { FolderGit2, Plus, ExternalLink, GitBranch, Calendar, X } from "lucide-react";
import { DataTable } from "@/components/DataTable";
import { api, RepositoryItem } from "@/lib/api";

export default function RepositoriesPage() {
  const [loading, setLoading] = useState(true);
  const [repos, setRepos] = useState<RepositoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoUrl, setNewRepoUrl] = useState("");

  const fetchRepos = async (currentOffset = 0) => {
    try {
      setLoading(true);
      const res = await api.getRepositories(20, currentOffset);
      setRepos(res.items || []);
      setTotal(res.total || 0);
    } catch (e: any) {
      if (e.message?.includes("401") || e.message?.includes("Unauthorized")) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("leakguard_token");
          window.location.href = "/login";
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepos(offset);
  }, [offset]);

  const handleCreateRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoName.trim()) return;
    try {
      await api.createRepository(newRepoName, newRepoUrl);
      setShowCreateModal(false);
      setNewRepoName("");
      setNewRepoUrl("");
      fetchRepos(offset);
    } catch (err) {
      alert(`Failed to create repository: ${(err as Error).message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-emerald-600" /> Repositories
          </h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Registered project repositories tracked by LeakGuard Control Plane.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" /> Add Repository
        </button>
      </div>

      <DataTable
        columns={[
          {
            header: "Repository Name",
            accessor: (r: RepositoryItem) => (
              <div className="flex items-center gap-2">
                <FolderGit2 className="w-4 h-4 text-emerald-600" />
                <span className="font-bold text-slate-900 text-xs">{r.name}</span>
              </div>
            ),
          },
          {
            header: "Default Branch",
            accessor: (r: RepositoryItem) => (
              <div className="flex items-center gap-1.5 text-xs text-slate-600 font-mono">
                <GitBranch className="w-3.5 h-3.5 text-emerald-600" />
                <span>{r.default_branch}</span>
              </div>
            ),
          },
          {
            header: "URL",
            accessor: (r: RepositoryItem) =>
              r.url ? (
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-xs text-emerald-700 hover:underline font-semibold"
                >
                  <span className="truncate max-w-xs">{r.url}</span>
                  <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              ) : (
                <span className="text-xs text-slate-400 font-medium">Local Repo</span>
              ),
          },
          {
            header: "Added Date",
            accessor: (r: RepositoryItem) => (
              <div className="flex items-center gap-1.5 text-xs text-slate-500 font-semibold">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
            ),
          },
        ]}
        data={repos}
        loading={loading}
        total={total}
        limit={20}
        offset={offset}
        onPageChange={setOffset}
        emptyText="No repositories registered"
        emptySubtext="Add your first repository or run a scan to auto-register."
      />

      {/* Create Repo Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl w-full max-w-md p-6 space-y-4 shadow-2xl text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-lg font-extrabold text-slate-900">Add New Repository</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRepo} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Repository Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. backend-service"
                  value={newRepoName}
                  onChange={(e) => setNewRepoName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">
                  Git URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="https://github.com/org/backend-service"
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-xs font-extrabold text-white shadow-md shadow-emerald-600/20 cursor-pointer"
                >
                  Save Repository
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
