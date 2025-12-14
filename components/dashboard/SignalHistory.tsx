'use client'

import React, { useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth-context'

interface HistoricalSignal {
  signal_id: string
  timestamp: string
  signal_data: {
    action: string
    strength: string
    confidence_score: number
    position_sizing: number
    risk_cluster: string
  }
  market_conditions: {
    sentiment_index: number
    sentiment_state: string
    market_regime: string
    price_level: number | null
  }
}

export default function SignalHistory() {
  const { user } = useAuth()
  const [signals, setSignals] = useState<HistoricalSignal[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSignalHistory = async () => {
    if (!user) return

    try {
      setLoading(true)
      setError(null)

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/get-signal-history?userId=${user.id}&limit=20`
      )

      if (!response.ok) {
        throw new Error('Failed to fetch signal history')
      }

      const data = await response.json()
      setSignals(data.signals || [])
    } catch (err) {
      console.error('Failed to load signal history:', err)
      setError('Failed to load signal history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSignalHistory()
  }, [user])

  const getActionColor = (action: string) => {
    switch (action.toUpperCase()) {
      case 'BUY':
        return 'text-emerald-600 bg-emerald-50 border border-emerald-200'
      case 'SELL':
        return 'text-red-600 bg-red-50 border border-red-200'
      case 'HOLD':
        return 'text-amber-600 bg-amber-50 border border-amber-200'
      default:
        return 'text-gray-600 bg-gray-50 border border-gray-200'
    }
  }

  const formatDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleDateString()
    } catch {
      return timestamp
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading signal history...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl shadow-sm border border-red-200 bg-red-50 p-6">
        <div className="text-center py-6">
          <div className="text-red-600 mb-4">{error}</div>
          <button 
            onClick={loadSignalHistory}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (signals.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="text-center py-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Signal History Yet
          </h3>
          <p className="text-gray-600">
            You'll see trading signals here starting from when you joined. New signals are generated weekly on Sundays.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900">Signal History</h2>
        <button 
          onClick={loadSignalHistory}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {signals.map((signal) => (
          <div key={signal.signal_id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-3">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getActionColor(signal.signal_data.action)}`}>
                  {signal.signal_data.action}
                </span>
                <span className="text-sm text-gray-600 font-medium">
                  {signal.signal_data.strength}
                </span>
                <span className="text-sm text-gray-500">
                  {(signal.signal_data.confidence_score * 100).toFixed(0)}% confidence
                </span>
              </div>
              <span className="text-sm text-gray-500">
                {formatDate(signal.timestamp)}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Position:</span>
                <span className="ml-2 font-medium">
                  {(signal.signal_data.position_sizing * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-600">Market Regime:</span>
                <span className="ml-2 font-medium">
                  {signal.market_conditions.market_regime}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-500">
          Showing last {signals.length} signals
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Last updated: {new Date().toLocaleTimeString()}
        </p>
      </div>
    </div>
  )
}
