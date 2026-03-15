import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Spinner from '../components/Spinner'

export default function Competitions() {
  useEffect(() => {
    document.title = 'Browse Competitions | UDL'
    return () => { document.title = 'United Degenerates League' }
  }, [])

  const { data: competitions, isLoading, isError } = useQuery({
    queryKey: ['all-competitions'],
    queryFn: async () => {
      const response = await api.get('/competitions')
      return response.data
    },
  })

  if (isLoading) {
    return <Spinner />
  }

  if (isError) {
    return (
      <div className="card text-center py-12">
        <p className="text-red-600 font-medium">Failed to load competitions.</p>
        <p className="text-gray-500 text-sm mt-2">Check your connection and try refreshing.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Browse Competitions</h1>
        <Link to="/competitions/create" className="btn btn-primary">
          Create Competition
        </Link>
      </div>

      {competitions && competitions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {competitions.map((comp: any) => (
            <div key={comp.id} className="card">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-semibold">{comp.name}</h3>
                <span
                  className={`badge capitalize ${
                    comp.status === 'active'
                      ? 'badge-in-progress'
                      : comp.status === 'upcoming'
                      ? 'badge-open'
                      : 'badge-final'
                  }`}
                >
                  {comp.status.replace(/_/g, ' ')}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-2 capitalize">{comp.mode.replace(/_/g, ' ')}</p>

              <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                <span>{comp.participant_count} participants</span>
                {comp.max_participants && (
                  <span>Max: {comp.max_participants}</span>
                )}
              </div>

              <Link
                to={`/competitions/${comp.id}`}
                className="btn btn-primary w-full"
              >
                {comp.user_is_participant ? 'View Details' : 'Join Competition'}
              </Link>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <p className="text-gray-600">No competitions available yet.</p>
        </div>
      )}
    </div>
  )
}
