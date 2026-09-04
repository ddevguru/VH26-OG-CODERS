"use client";

import React, { useEffect, useState } from "react";
import { FolderGit2, Plus, ExternalLink, GitBranch, ShieldCheck } from "lucide-react";
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
    } catch (e) {
      console.error(e);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-indigo-400" /> Repositories
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Registered project repositories tracked by LeakGuard Control Plane.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
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
                <FolderGit2 className="w-4 h-4 text-indigo-400" />
                <span className="font-bold text-white">{r.name}</span>
              </div>
            ),
          },
          {
            header: "Default Branch",
            accessor: (r: RepositoryItem) => (
              <div className="flex items-center gap-1.5 text-xs text-gray-300 font-mono">
                <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
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
                  className="text-indigo-400 hover:underline flex items-center gap-1 text-xs"
                >
                  {r.url.replace(/^https?:\/\//, "")} <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                <span className="text-gray-400 text-xs">—</span>
              ),
          },
          {
            header: "Health Status",
            accessor: () => (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/70 text-emerald-400 border border-emerald-800/60">
                <ShieldCheck className="w-3.5 h-3.5" /> Protected
              </span>
            ),
          },
          {
            header: "Created At",
            accessor: (r: RepositoryItem) =>
              new Date(r.created_at).toLocaleDateString(),
          },
        ]}
        data={repos}
        loading={loading}
        total={total}
        limit={20}
        offset={offset}
        onPageChange={setOffset}
        emptyText="No repositories configured"
        emptySubtext="Add your first repository or run 'leakguard upload --repo <name>' to automatically register a repository."
      />

      {/* Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0e1626] border border-gray-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Add New Repository</h3>
            <form onSubmit={handleCreateRepo} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Repository Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. backend-service"
                  value={newRepoName}
                  onChange={(e) => setNewRepoName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Git Repository URL (Optional)</label>
                <input
                  type="url"
                  placeholder="https://github.com/acme/backend-service"
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-semibold text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/30"
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
