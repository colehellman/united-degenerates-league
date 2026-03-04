import { useEffect, useRef, useCallback, useState } from 'react'

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
  .replace(/^http/, 'ws')

interface ScoreUpdate {
  game_id: string
  status: string
  home_score: number | null
  away_score: number | null
  home_team_id: string
  away_team_id: string
  winner_team_id: string | null
}

interface ScoreMessage {
  type: 'score_update'
  games: ScoreUpdate[]
}

/**
 * React hook that connects to the live scores WebSocket.
 *
 * Usage:
 *   const { scores, isConnected } = useLiveScores()
 *
 * `scores` is a Map<game_id, ScoreUpdate> that updates in real-time.
 * Auto-reconnects on disconnect with exponential backoff.
 */
export function useLiveScores() {
  const [scores, setScores] = useState<Map<string, ScoreUpdate>>(new Map())
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_URL}/ws/scores`)

    ws.onopen = () => {
      setIsConnected(true)
      retryRef.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data: ScoreMessage = JSON.parse(event.data)
        if (data.type === 'score_update') {
          setScores((prev) => {
            const next = new Map(prev)
            for (const game of data.games) {
              next.set(game.game_id, game)
            }
            return next
          })
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      // Exponential backoff: 1s, 2s, 4s, 8s, ... max 30s
      const delay = Math.min(1000 * 2 ** retryRef.current, 30000)
      retryRef.current++
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { scores, isConnected }
}
