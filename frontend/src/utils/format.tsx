export const formatGameTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export const isGameLocked = (game: any) => {
  const startTime = new Date(game.scheduled_start_time)
  return startTime <= new Date() || game.status === 'in_progress' || game.status === 'final'
}

export const formatDate = (isoString: string) => {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export const getGameStatusBadge = (game: any) => {
  switch (game.status) {
    case 'in_progress':
      return (
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-red-100 text-red-700 rounded-full animate-pulse">
          Live
        </span>
      )
    case 'final':
      return (
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-600 rounded-full">
          Final
        </span>
      )
    case 'cancelled':
    case 'postponed':
      return (
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-yellow-100 text-yellow-700 rounded-full">
          {game.status}
        </span>
      )
    default:
      return null
  }
}
