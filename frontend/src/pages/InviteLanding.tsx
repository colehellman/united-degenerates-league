import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../services/authStore'
import { resolveInviteToken, joinViaInvite } from '../services/api'
import Spinner from '../components/Spinner'

export default function InviteLanding() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState('')

  const { data: invite, isLoading, error } = useQuery({
    queryKey: ['invite', token],
    queryFn: () => resolveInviteToken(token!),
    enabled: !!token,
    retry: false,
  })

  const handleJoin = async () => {
    if (!invite || !token) return
    setJoining(true)
    setJoinError('')
    try {
      await joinViaInvite(invite.competition_id, token)
      navigate(`/competitions/${invite.competition_id}`)
    } catch (err: any) {
      setJoinError(err.response?.data?.detail || 'Failed to join competition')
    } finally {
      setJoining(false)
    }
  }

  if (isLoading) {
    return <Spinner />
  }

  if (error) {
    const status = (error as any)?.response?.status
    if (status === 404) {
      return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
          <div className="card text-center max-w-md">
            <h2 className="text-xl font-bold text-gray-900 mb-2">Invalid Invite</h2>
            <p className="text-gray-600 mb-4">This invite link is invalid or has expired.</p>
            <Link to="/login" className="btn btn-primary">Go to Login</Link>
          </div>
        </div>
      )
    }
    if (status === 410) {
      return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
          <div className="card text-center max-w-md">
            <h2 className="text-xl font-bold text-gray-900 mb-2">Competition Ended</h2>
            <p className="text-gray-600 mb-4">This competition has already ended.</p>
            <Link to="/login" className="btn btn-primary">Go to Login</Link>
          </div>
        </div>
      )
    }
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <div className="card text-center max-w-md">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">Something went wrong. Please try again.</p>
          <Link to="/login" className="btn btn-primary">Go to Login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="card text-center max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          You've been invited!
        </h1>
        <p className="text-lg text-gray-700 mb-6">{invite?.competition_name}</p>

        {joinError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            {joinError}
          </div>
        )}

        {isAuthenticated ? (
          <button
            onClick={handleJoin}
            disabled={joining}
            className="btn btn-primary w-full"
          >
            {joining ? 'Joining...' : 'Join Competition'}
          </button>
        ) : (
          <div className="space-y-3">
            <Link
              to={`/register?redirect=/invite/${token}`}
              className="btn btn-primary w-full block"
            >
              Sign Up to Join
            </Link>
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link to={`/login?redirect=/invite/${token}`} className="text-primary-600 hover:text-primary-700 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
