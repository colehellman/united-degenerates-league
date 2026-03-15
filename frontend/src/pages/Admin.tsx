import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuthStore } from '../services/authStore'
import api from '../services/api'
import Spinner from '../components/Spinner'

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

type AdminTab = 'overview' | 'users' | 'competitions' | 'bug-reports' | 'audit-logs'

const TAB_LABELS: Record<AdminTab, string> = {
  'overview': 'Overview',
  'users': 'Users',
  'competitions': 'Competitions',
  'bug-reports': 'Bug Reports',
  'audit-logs': 'Audit Logs',
}

export default function Admin() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<AdminTab>('overview')

  if (user && user.role !== 'global_admin') {
    return <Navigate to="/" replace />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl sm:text-3xl font-bold">Admin Panel</h1>
        <span className="badge bg-red-100 text-red-700 text-xs sm:text-sm">
          Global Admin
        </span>
      </div>

      {/* Tabs — scrollable on mobile */}
      <div className="border-b border-gray-200 -mx-4 px-4 sm:mx-0 sm:px-0 overflow-x-auto">
        <nav className="flex min-w-max sm:min-w-0 gap-1 sm:gap-6">
          {(Object.keys(TAB_LABELS) as AdminTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-2 sm:px-1 text-sm font-medium border-b-2 transition whitespace-nowrap ${
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

      {activeTab === 'overview' && <OverviewTab />}
      {activeTab === 'users' && <UsersTab queryClient={queryClient} />}
      {activeTab === 'competitions' && <CompetitionsTab />}
      {activeTab === 'bug-reports' && <BugReportsTab queryClient={queryClient} />}
      {activeTab === 'audit-logs' && <AuditLogsTab />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared badge helpers
// ---------------------------------------------------------------------------

const ROLE_BADGE: Record<string, string> = {
  global_admin: 'bg-red-100 text-red-700',
  league_admin: 'bg-yellow-100 text-yellow-700',
  user: 'bg-gray-100 text-gray-600',
}

const STATUS_BADGE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  suspended: 'bg-orange-100 text-orange-700',
  banned: 'bg-red-100 text-red-700',
  pending_deletion: 'bg-yellow-100 text-yellow-700',
  deleted: 'bg-gray-100 text-gray-400',
}

// ---------------------------------------------------------------------------
// Overview Tab — platform stats
// ---------------------------------------------------------------------------

function OverviewTab() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: async () => {
      const res = await api.get('/admin/stats')
      return res.data
    },
  })

  if (isLoading) return <Spinner />

  if (!stats) return null

  const statCards = [
    { label: 'Total Users', value: stats.total_users, color: 'bg-blue-50 text-blue-700' },
    { label: 'Active Competitions', value: stats.active_competitions, color: 'bg-green-50 text-green-700' },
    { label: 'Total Competitions', value: stats.total_competitions, color: 'bg-purple-50 text-purple-700' },
    { label: 'Total Picks', value: stats.total_picks, color: 'bg-orange-50 text-orange-700' },
    { label: 'Total Games', value: stats.total_games, color: 'bg-gray-50 text-gray-700' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {statCards.map((s) => (
        <div key={s.label} className={`rounded-lg p-4 ${s.color}`}>
          <div className="text-2xl sm:text-3xl font-bold">{s.value}</div>
          <div className="text-sm mt-1 opacity-80">{s.label}</div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Users Tab — list + inline actions (status change, role change)
// ---------------------------------------------------------------------------

function UsersTab({ queryClient }: { queryClient: any }) {
  const { user: currentUser } = useAuthStore()

  const { data: users, isLoading, isError } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => {
      const res = await api.get('/admin/users')
      return res.data
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ userId, status, reason }: { userId: string; status: string; reason?: string }) =>
      api.patch(`/admin/users/${userId}/status`, { status, reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User status updated')
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to update status'),
  })

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.patch(`/admin/users/${userId}/role`, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      toast.success('User role updated')
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to update role'),
  })

  if (isLoading) return <Spinner />

  if (isError) {
    return (
      <div className="card text-center py-12">
        <p className="text-red-600 font-medium">Failed to load users.</p>
      </div>
    )
  }

  if (!users || users.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No users found.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Mobile: card layout. Desktop: table */}
      <div className="hidden lg:block card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Username</th>
              <th className="px-4 py-3 text-left font-semibold">Email</th>
              <th className="px-4 py-3 text-left font-semibold">Role</th>
              <th className="px-4 py-3 text-left font-semibold">Status</th>
              <th className="px-4 py-3 text-left font-semibold">Joined</th>
              <th className="px-4 py-3 text-left font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map((u: any) => {
              const isSelf = u.id === currentUser?.id
              return (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{u.username}</td>
                  <td className="px-4 py-3 text-gray-600 truncate max-w-[200px]">{u.email}</td>
                  <td className="px-4 py-3">
                    {isSelf ? (
                      <span className={`px-2 py-1 rounded text-xs font-medium ${ROLE_BADGE[u.role] ?? 'bg-gray-100'}`}>
                        {u.role}
                      </span>
                    ) : (
                      <select
                        value={u.role}
                        onChange={(e) => roleMutation.mutate({ userId: u.id, role: e.target.value })}
                        disabled={roleMutation.isPending}
                        className="input py-1 text-xs w-auto"
                      >
                        <option value="user">user</option>
                        <option value="global_admin">global_admin</option>
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {isSelf ? (
                      <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_BADGE[u.status] ?? 'bg-gray-100'}`}>
                        {u.status}
                      </span>
                    ) : (
                      <select
                        value={u.status}
                        onChange={(e) => statusMutation.mutate({ userId: u.id, status: e.target.value })}
                        disabled={statusMutation.isPending}
                        className="input py-1 text-xs w-auto"
                      >
                        <option value="active">Active</option>
                        <option value="suspended">Suspended</option>
                        <option value="banned">Banned</option>
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {isSelf ? '—' : 'Editable via dropdowns'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile card layout */}
      <div className="lg:hidden space-y-3">
        {users.map((u: any) => {
          const isSelf = u.id === currentUser?.id
          return (
            <div key={u.id} className="card space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-semibold">{u.username}</div>
                  <div className="text-sm text-gray-500 break-all">{u.email}</div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium shrink-0 ${ROLE_BADGE[u.role] ?? 'bg-gray-100'}`}>
                  {u.role}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className={`px-2 py-0.5 rounded font-medium ${STATUS_BADGE[u.status] ?? 'bg-gray-100'}`}>
                  {u.status}
                </span>
                <span>Joined {new Date(u.created_at).toLocaleDateString()}</span>
              </div>
              {!isSelf && (
                <div className="flex gap-2 pt-1">
                  <select
                    value={u.role}
                    onChange={(e) => roleMutation.mutate({ userId: u.id, role: e.target.value })}
                    disabled={roleMutation.isPending}
                    className="input py-1.5 text-xs flex-1"
                  >
                    <option value="user">Role: User</option>
                    <option value="global_admin">Role: Admin</option>
                  </select>
                  <select
                    value={u.status}
                    onChange={(e) => statusMutation.mutate({ userId: u.id, status: e.target.value })}
                    disabled={statusMutation.isPending}
                    className="input py-1.5 text-xs flex-1"
                  >
                    <option value="active">Active</option>
                    <option value="suspended">Suspended</option>
                    <option value="banned">Banned</option>
                  </select>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Competitions Tab — all competitions + participant management
// ---------------------------------------------------------------------------

function CompetitionsTab() {
  const [selectedComp, setSelectedComp] = useState<string>('')
  const queryClient = useQueryClient()

  const { data: competitions, isLoading: compsLoading } = useQuery({
    queryKey: ['admin-competitions'],
    queryFn: async () => {
      const res = await api.get('/admin/competitions')
      return res.data
    },
  })

  const { data: participants, isLoading: participantsLoading } = useQuery({
    queryKey: ['admin-participants', selectedComp],
    queryFn: async () => {
      const res = await api.get(`/admin/competitions/${selectedComp}/participants`)
      return res.data
    },
    enabled: !!selectedComp,
  })

  const removeParticipantMutation = useMutation({
    mutationFn: ({ compId, userId }: { compId: string; userId: string }) =>
      api.delete(`/admin/competitions/${compId}/participants/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-participants', selectedComp] })
      toast.success('Participant removed')
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to remove participant'),
  })

  if (compsLoading) return <Spinner />

  return (
    <div className="space-y-4">
      {/* Competition selector */}
      <div className="card">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select a competition to manage
        </label>
        <select
          value={selectedComp}
          onChange={(e) => setSelectedComp(e.target.value)}
          className="input"
        >
          <option value="">Choose competition...</option>
          {(competitions ?? []).map((c: any) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.status} — {c.participant_count} participants)
            </option>
          ))}
        </select>
      </div>

      {/* Competitions overview */}
      {!selectedComp && competitions && competitions.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {competitions.map((c: any) => (
            <button
              key={c.id}
              onClick={() => setSelectedComp(c.id)}
              className="card text-left hover:shadow-lg transition-shadow"
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold truncate mr-2">{c.name}</h3>
                <span className={`badge shrink-0 capitalize text-xs ${
                  c.status === 'active' ? 'badge-in-progress'
                    : c.status === 'upcoming' ? 'badge-open'
                    : 'badge-final'
                }`}>{c.status}</span>
              </div>
              <div className="text-sm text-gray-500">
                {c.participant_count} participants
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Participants table */}
      {selectedComp && participantsLoading && <Spinner />}

      {selectedComp && !participantsLoading && participants && participants.length === 0 && (
        <div className="card text-center py-12 text-gray-500">
          No participants enrolled yet.
        </div>
      )}

      {selectedComp && !participantsLoading && participants && participants.length > 0 && (
        <div className="card overflow-x-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">
              Participants ({participants.length})
            </h3>
            <button
              onClick={() => setSelectedComp('')}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              Back to list
            </button>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Username</th>
                <th className="px-4 py-3 text-right font-semibold">Points</th>
                <th className="px-4 py-3 text-right font-semibold">W</th>
                <th className="px-4 py-3 text-right font-semibold">L</th>
                <th className="px-4 py-3 text-right font-semibold">Acc%</th>
                <th className="px-4 py-3 text-left font-semibold">Joined</th>
                <th className="px-4 py-3 text-left font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {participants.map((p: any) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{p.username}</td>
                  <td className="px-4 py-3 text-right font-semibold">{p.total_points}</td>
                  <td className="px-4 py-3 text-right text-green-700">{p.total_wins}</td>
                  <td className="px-4 py-3 text-right text-red-600">{p.total_losses}</td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {p.accuracy_percentage.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(p.joined_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => {
                        if (confirm(`Remove ${p.username} from this competition?`)) {
                          removeParticipantMutation.mutate({ compId: selectedComp, userId: p.user_id })
                        }
                      }}
                      disabled={removeParticipantMutation.isPending}
                      className="text-red-600 hover:text-red-800 text-xs font-medium"
                    >
                      Remove
                    </button>
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

// ---------------------------------------------------------------------------
// Bug Reports Tab
// ---------------------------------------------------------------------------

function BugReportsTab({ queryClient }: { queryClient: any }) {
  const { data: reports, isLoading, isError } = useQuery({
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

  if (isLoading) return <Spinner />

  if (isError) {
    return (
      <div className="card text-center py-12">
        <p className="text-red-600 font-medium">Failed to load bug reports.</p>
      </div>
    )
  }

  if (!reports || reports.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No bug reports submitted yet.
      </div>
    )
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Status</th>
              <th className="px-4 py-3 text-left font-semibold">Category</th>
              <th className="px-4 py-3 text-left font-semibold">Title</th>
              <th className="px-4 py-3 text-left font-semibold">Description</th>
              <th className="px-4 py-3 text-left font-semibold">Filed</th>
              <th className="px-4 py-3 text-left font-semibold">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {reports.map((r: any) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${BUG_STATUS_COLORS[r.status] || ''}`}>
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

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {reports.map((r: any) => (
          <div key={r.id} className="card space-y-2">
            <div className="flex items-center justify-between">
              <span className={`px-2 py-1 rounded text-xs font-medium ${BUG_STATUS_COLORS[r.status] || ''}`}>
                {BUG_STATUS_LABELS[r.status] || r.status}
              </span>
              <span className="text-xs text-gray-400 capitalize">{r.category}</span>
            </div>
            <h4 className="font-medium text-sm">{r.title}</h4>
            <p className="text-sm text-gray-600 line-clamp-2">{r.description}</p>
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-gray-400">
                {new Date(r.created_at).toLocaleDateString()}
              </span>
              <select
                value={r.status}
                onChange={(e) => updateStatusMutation.mutate({ id: r.id, status: e.target.value })}
                disabled={updateStatusMutation.isPending}
                className="input py-1 text-xs w-auto"
              >
                {Object.entries(BUG_STATUS_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Audit Logs Tab
// ---------------------------------------------------------------------------

const AUDIT_ACTION_LABELS: Record<string, string> = {
  competition_created: 'Competition Created',
  competition_deleted: 'Competition Deleted',
  competition_status_changed: 'Status Changed',
  competition_settings_changed: 'Settings Changed',
  user_deleted: 'User Deleted',
  user_role_changed: 'Role Changed',
  user_suspended: 'User Suspended',
  user_banned: 'User Banned',
  user_reactivated: 'User Reactivated',
  admin_added: 'Admin Added',
  admin_removed: 'Admin Removed',
  score_corrected: 'Score Corrected',
  winner_designated: 'Winner Designated',
  participant_removed: 'Participant Removed',
  join_request_approved: 'Join Approved',
  join_request_rejected: 'Join Rejected',
}

function AuditLogsTab() {
  const { data: logs, isLoading, isError } = useQuery({
    queryKey: ['admin-audit-logs'],
    queryFn: async () => {
      const res = await api.get('/admin/audit-logs', { params: { limit: 100 } })
      return res.data
    },
  })

  if (isLoading) return <Spinner />

  if (isError) {
    return (
      <div className="card text-center py-12">
        <p className="text-red-600 font-medium">Failed to load audit logs.</p>
      </div>
    )
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-500">
        No audit log entries yet.
      </div>
    )
  }

  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Timestamp</th>
              <th className="px-4 py-3 text-left font-semibold">Action</th>
              <th className="px-4 py-3 text-left font-semibold">Target</th>
              <th className="px-4 py-3 text-left font-semibold">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.map((log: any) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-medium text-sm">
                  {AUDIT_ACTION_LABELS[log.action] || log.action}
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  <span className="capitalize">{log.target_type}</span>
                  {log.target_id && (
                    <span className="text-gray-400 font-mono ml-1">
                      {log.target_id.slice(0, 8)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 max-w-[300px] truncate text-xs"
                    title={log.details ? JSON.stringify(log.details, null, 2) : ''}>
                  {log.details ? formatDetails(log.details) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {logs.map((log: any) => (
          <div key={log.id} className="card space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-medium text-sm">
                {AUDIT_ACTION_LABELS[log.action] || log.action}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(log.created_at).toLocaleString([], {
                  month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                })}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              <span className="capitalize">{log.target_type}</span>
              {log.target_id && (
                <span className="text-gray-400 font-mono ml-1">{log.target_id.slice(0, 8)}</span>
              )}
            </div>
            {log.details && (
              <div className="text-xs text-gray-400 break-words">
                {formatDetails(log.details)}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}

function formatDetails(details: Record<string, any>): string {
  const parts: string[] = []
  for (const [key, value] of Object.entries(details)) {
    if (value === null || value === undefined) continue
    const label = key.replace(/_/g, ' ')
    if (Array.isArray(value)) {
      parts.push(`${label}: ${value.join(', ')}`)
    } else {
      parts.push(`${label}: ${value}`)
    }
  }
  return parts.join(' | ')
}
