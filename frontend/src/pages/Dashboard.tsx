import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../services/api'
import Spinner from '../components/Spinner'

export default function Dashboard() {
  useEffect(() => {
    document.title = 'Dashboard | UDL'
    return () => { document.title = 'United Degenerates League' }
  }, [])

  const { data: competitions, isLoading, isError } = useQuery({
    queryKey: ['competitions'],
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

  const activeCompetitions = competitions?.filter((c: any) => c.status === 'active') || []
  const upcomingCompetitions = competitions?.filter((c: any) => c.status === 'upcoming') || []

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex gap-3">
          <Link to="/competitions/create" className="btn btn-primary">
            Create Competition
          </Link>
          <Link to="/competitions" className="btn bg-gray-200 text-gray-700 hover:bg-gray-300">
            Browse Competitions
          </Link>
        </div>
      </div>

      {activeCompetitions.length === 0 && upcomingCompetitions.length === 0 && (
        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">
            You haven't joined any competitions yet
          </h2>
          <p className="text-gray-600 mb-6">
            Create or join one now to start competing!
          </p>
          <Link to="/competitions" className="btn btn-primary">
            Browse Competitions
          </Link>
        </div>
      )}

      {activeCompetitions.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Active Competitions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeCompetitions.map((comp: any) => (
              <Link
                key={comp.id}
                to={`/competitions/${comp.id}`}
                className="card hover:shadow-lg transition-shadow"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-semibold">{comp.name}</h3>
                  <span className="badge badge-in-progress">Active</span>
                </div>
                <p className="text-sm text-gray-600 mb-2 capitalize">{comp.mode.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-500">
                  {comp.participant_count} participants
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {upcomingCompetitions.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">Upcoming Competitions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingCompetitions.map((comp: any) => (
              <Link
                key={comp.id}
                to={`/competitions/${comp.id}`}
                className="card hover:shadow-lg transition-shadow"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-semibold">{comp.name}</h3>
                  <span className="badge badge-open">Upcoming</span>
                </div>
                <p className="text-sm text-gray-600 mb-2 capitalize">{comp.mode.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-500">
                  {comp.participant_count} participants
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
