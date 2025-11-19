import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'

export default function Competitions() {
  const { data: competitions, isLoading } = useQuery({
    queryKey: ['all-competitions'],
    queryFn: async () => {
      const response = await api.get('/competitions')
      return response.data
    },
  })

  if (isLoading) {
    return <div className="text-center py-8">Loading competitions...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Browse Competitions</h1>
      </div>

      {competitions && competitions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {competitions.map((comp: any) => (
            <div key={comp.id} className="card">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-xl font-semibold">{comp.name}</h3>
                <span
                  className={`badge ${
                    comp.status === 'active'
                      ? 'badge-in-progress'
                      : comp.status === 'upcoming'
                      ? 'badge-open'
                      : 'badge-final'
                  }`}
                >
                  {comp.status}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-2 capitalize">{comp.mode.replace('_', ' ')}</p>

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
