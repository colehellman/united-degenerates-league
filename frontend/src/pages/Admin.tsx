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

type AdminTab = 'bug-reports' | 'audit-logs' | 'users' | 'participants'

const TAB_LABELS: Record<AdminTab, string> = {
  'bug-reports': 'Bug Reports',
  'audit-logs': 'Audit Logs',
  'users': 'Users',
  'participants': 'Participants',
}

export default function Admin() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<AdminTab>('bug-reports')

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
          {(Object.keys(TAB_LABELS) as AdminTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'bug-reports' && <BugReportsTab queryClient={queryClient} />}
      {activeTab === 'audit-logs' && <AuditLogsTab />}
      {activeTab === 'users' && <UsersTab />}
      {activeTab === 'participants' && <ParticipantsTab />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Role / Status badge helpers (shared across Users and Participants tabs)
// ---------------------------------------------------------------------------

const ROLE_BADGE: Record<string, string> = {
  global_admin: 'bg-red-100 text-red-700',
  league_admin: 'bg-yellow-100 text-yellow-700',
  user: 'bg-gray-100 text-gray-600',
}

const STATUS_BADGE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  pending_deletion: 'bg-yellow-100 text-yellow-700',
  deleted: 'bg-gray-100 text-gray-400',
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

// ---------------------------------------------------------------------------
// Users Tab — all registered (non-deleted) platform users
// ---------------------------------------------------------------------------

function UsersTab() {
  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/admin/users')
      return res.data
    },
  })

  if (isLoading) return <p className="text-gray-600">Loading users…</p>

  if (!users || users.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No users found.
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold">Username</th>
            <th className="px-4 py-3 text-left font-semibold">Email</th>
            <th className="px-4 py-3 text-left font-semibold">Role</th>
            <th className="px-4 py-3 text-left font-semibold">Status</th>
            <th className="px-4 py-3 text-left font-semibold">Joined</th>
            <th className="px-4 py-3 text-left font-semibold">Last Login</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {users.map((u: any) => (
            <tr key={u.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium">{u.username}</td>
              <td className="px-4 py-3 text-gray-600">{u.email}</td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${ROLE_BADGE[u.role] ?? 'bg-gray-100 text-gray-600'}`}>
                  {u.role}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_BADGE[u.status] ?? 'bg-gray-100 text-gray-400'}`}>
                  {u.status}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                {new Date(u.created_at).toLocaleDateString()}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Participants Tab — select a competition, then list enrolled users with stats
// ---------------------------------------------------------------------------

function ParticipantsTab() {
  const [selectedComp, setSelectedComp] = useState<string>('')

  const { data: competitions, isLoading: compsLoading } = useQuery({
    queryKey: ['competitions-list'],
    queryFn: async () => {
      const res = await api.get('/competitions')
      return res.data
    },
  })

  const { data: participants, isLoading: participantsLoading } = useQuery({
    queryKey: ['admin-participants', selectedComp],
    queryFn: async () => {
      const res = await api.get(`/admin/competitions/${selectedComp}/participants`)
      return res.data
    },
    // Only fire once a competition is selected
    enabled: !!selectedComp,
  })

  return (
    <div className="space-y-4">
      {/* Competition selector */}
      <div className="card flex items-center gap-4">
        <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
          Competition
        </label>
        {compsLoading ? (
          <p className="text-gray-500 text-sm">Loading competitions…</p>
        ) : (
          <select
            value={selectedComp}
            onChange={(e) => setSelectedComp(e.target.value)}
            className="input max-w-sm"
          >
            <option value="">Select a competition…</option>
            {(competitions ?? []).map((c: any) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Participants table */}
      {!selectedComp && (
        <div className="card text-center py-12 text-gray-500">
          Select a competition above to view its participants.
        </div>
      )}

      {selectedComp && participantsLoading && (
        <p className="text-gray-600">Loading participants…</p>
      )}

      {selectedComp && !participantsLoading && participants && participants.length === 0 && (
        <div className="card text-center py-12 text-gray-500">
          No participants enrolled in this competition yet.
        </div>
      )}

      {selectedComp && !participantsLoading && participants && participants.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Username</th>
                <th className="px-4 py-3 text-left font-semibold">Email</th>
                <th className="px-4 py-3 text-right font-semibold">Points</th>
                <th className="px-4 py-3 text-right font-semibold">Wins</th>
                <th className="px-4 py-3 text-right font-semibold">Losses</th>
                <th className="px-4 py-3 text-right font-semibold">Accuracy</th>
                <th className="px-4 py-3 text-left font-semibold">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {participants.map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.username}</td>
                  <td className="px-4 py-3 text-gray-600">{p.email}</td>
                  <td className="px-4 py-3 text-right font-semibold">{p.total_points}</td>
                  <td className="px-4 py-3 text-right text-green-700">{p.total_wins}</td>
                  <td className="px-4 py-3 text-right text-red-600">{p.total_losses}</td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {p.accuracy_percentage.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(p.joined_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
