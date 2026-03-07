import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuthStore } from '../services/authStore'
import api from '../services/api'

const BUG_STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  in_review: 'In Review',
  resolved: 'Resolved',
  closed: 'Closed',
}

const BUG_STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-100 text-red-700',
  in_review: 'bg-yellow-100 text-yellow-700',
  resolved: 'bg-green-100 text-green-700',
  closed: 'bg-gray-100 text-gray-600',
}

export default function Admin() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'bug-reports' | 'audit-logs'>('bug-reports')

  // Redirect non-admins
  if (user && user.role !== 'global_admin') {
    return <Navigate to="/" replace />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Admin Panel</h1>
        <span className="badge bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-medium">
          Global Admin
        </span>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {(['bug-reports', 'audit-logs'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'bug-reports' ? 'Bug Reports' : 'Audit Logs'}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'bug-reports' && <BugReportsTab queryClient={queryClient} />}
      {activeTab === 'audit-logs' && <AuditLogsTab />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Bug Reports Tab
// ---------------------------------------------------------------------------

function BugReportsTab({ queryClient }: { queryClient: any }) {
  const { data: reports, isLoading } = useQuery({
    queryKey: ['admin-bug-reports'],
    queryFn: async () => {
      const res = await api.get('/bug-reports')
      return res.data
    },
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch(`/bug-reports/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-bug-reports'] })
      toast.success('Status updated')
    },
    onError: () => toast.error('Failed to update status'),
  })

  if (isLoading) return <p className="text-gray-600">Loading bug reports…</p>

  if (!reports || reports.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No bug reports submitted yet.
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">Status</th>
            <th className="px-4 py-3 text-left font-semibold">Category</th>
            <th className="px-4 py-3 text-left font-semibold">Title</th>
            <th className="px-4 py-3 text-left font-semibold">Description</th>
            <th className="px-4 py-3 text-left font-semibold">Page</th>
            <th className="px-4 py-3 text-left font-semibold">Filed</th>
            <th className="px-4 py-3 text-left font-semibold">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {reports.map((r: any) => (
            <tr key={r.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <span className={`badge px-2 py-1 rounded text-xs font-medium ${BUG_STATUS_COLORS[r.status] || ''}`}>
                  {BUG_STATUS_LABELS[r.status] || r.status}
                </span>
              </td>
              <td className="px-4 py-3 capitalize text-gray-600">{r.category}</td>
              <td className="px-4 py-3 font-medium max-w-[200px] truncate" title={r.title}>
                {r.title}
              </td>
              <td className="px-4 py-3 text-gray-600 max-w-[280px] truncate" title={r.description}>
                {r.description}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{r.page_url || '—'}</td>
              <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                {new Date(r.created_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3">
                <select
                  value={r.status}
                  onChange={(e) => updateStatusMutation.mutate({ id: r.id, status: e.target.value })}
                  disabled={updateStatusMutation.isPending}
                  className="input py-1 text-xs"
                >
                  {Object.entries(BUG_STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Audit Logs Tab
// ---------------------------------------------------------------------------

function AuditLogsTab() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['admin-audit-logs'],
    queryFn: async () => {
      const res = await api.get('/admin/audit-logs', { params: { limit: 100 } })
      return res.data
    },
  })

  if (isLoading) return <p className="text-gray-600">Loading audit logs…</p>

  if (!logs || logs.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No audit log entries yet.
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">Timestamp</th>
            <th className="px-4 py-3 text-left font-semibold">Action</th>
            <th className="px-4 py-3 text-left font-semibold">Target Type</th>
            <th className="px-4 py-3 text-left font-semibold">Target ID</th>
            <th className="px-4 py-3 text-left font-semibold">Details</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {logs.map((log: any) => (
            <tr key={log.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                {new Date(log.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 font-medium">{log.action}</td>
              <td className="px-4 py-3 text-gray-600 capitalize">{log.target_type}</td>
              <td className="px-4 py-3 text-gray-400 text-xs font-mono">
                {log.target_id ? log.target_id.slice(0, 8) + '…' : '—'}
              </td>
              <td className="px-4 py-3 text-gray-600 max-w-[300px] truncate text-xs"
                  title={JSON.stringify(log.details)}>
                {log.details ? JSON.stringify(log.details) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
