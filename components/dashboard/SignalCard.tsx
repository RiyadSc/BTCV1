'use client'

import React, { useState, useEffect } from 'react'

// Custom hook for countdown to 10 PM EDT of next day
const useCountdownTo10PM = (signalTimestamp: string) => {
  const [countdown, setCountdown] = useState('')
  const [lastSignalTime, setLastSignalTime] = useState(signalTimestamp)

  useEffect(() => {
    const calculateNext10PMEDT = () => {
      const now = new Date()
      
      // 10 PM EDT = 2 AM UTC the following day
      // Since EDT is UTC-4, we need to target 2 AM UTC
      const target = new Date()
      target.setUTCHours(2, 0, 0, 0) // 2 AM UTC = 10 PM EDT
      
      // If it's already past 2 AM UTC today, set target to tomorrow
      if (now >= target) {
        target.setUTCDate(target.getUTCDate() + 1)
      }
      
      return target
    }

    const updateCountdown = () => {
      const now = new Date()
      const target = calculateNext10PMEDT()
      
      const diff = target.getTime() - now.getTime()
      
      if (diff <= 0) {
        setCountdown('0h 0m')
        return
      }
      
      const hours = Math.floor(diff / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      
      setCountdown(`${hours}h ${minutes}m`)
    }

    // Update immediately
    updateCountdown()
    
    // Update every minute
    const interval = setInterval(updateCountdown, 60000)
    
    return () => clearInterval(interval)
  }, [lastSignalTime]) // Re-run when signal changes

  // Reset countdown when new signal is detected
  useEffect(() => {
    if (signalTimestamp !== lastSignalTime) {
      setLastSignalTime(signalTimestamp)
    }
  }, [signalTimestamp, lastSignalTime])

  return countdown
}

interface SignalCardProps {
  signal: {
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
      momentum_profile: {
        short_term_trend: string
        momentum_7d: number
        momentum_30d: number
      }
      volatility_index: number
    }
    risk_assessment: {
      volatility_percentile: number
      drawdown_risk: number
      momentum_risk: string
      regime_stability: string
      overall_risk_score: number
    }
    recommendation: {
      action: string
      reasoning: string
      allocation_guidance: string
      execution_strategy: string
      risk_management: string
    }
    is_previous_day?: boolean
    message?: string
  } | null
  signalLoading: boolean
  signalError: string | null
  onRefresh: () => void
}

export default function SignalCard({ signal, signalLoading, signalError, onRefresh }: SignalCardProps) {
  const countdown = useCountdownTo10PM(signal?.timestamp || '')
  
  // Always render the header with timer
  const renderHeader = () => (
    <div className="flex items-center justify-between mb-8">
      <div>
        <div className="flex items-center gap-4 mb-2">
          <h2 className="text-2xl font-bold text-gray-900">
            Trading Signal
          </h2>
          <div className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 rounded-full shadow-lg">
            <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
            <span className="text-sm font-semibold">Next Update In:</span>
            <span className="text-lg font-bold font-mono">{countdown}</span>
          </div>
        </div>
      </div>
    </div>
  )

  if (signalLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        {renderHeader()}
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Generating trading signal...</span>
        </div>
      </div>
    )
  }

  if (signalError) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        {renderHeader()}
        <div className="text-center py-6">
          <div className="text-red-600 mb-4">{signalError}</div>
          <button 
            onClick={onRefresh}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            Retry Signal Generation
          </button>
        </div>
      </div>
    )
  }

  if (!signal || !signal.signal_data) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        {renderHeader()}
        <div className="text-center py-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Signal Available Today
          </h3>
          <p className="text-gray-600 mb-4">
            Daily trading signals are generated automatically. Check back later for today's signal.
          </p>
          <button
            onClick={onRefresh}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
          >
            Refresh Signal
          </button>
        </div>
      </div>
    )
  }

  const getActionColor = (action: string) => {
    switch (action.toUpperCase()) {
      case 'BUY':
        return 'text-emerald-600 bg-emerald-50 border-emerald-200'
      case 'SELL':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'HOLD':
        return 'text-amber-600 bg-amber-50 border-amber-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getStrengthColor = (strength: string) => {
    switch (strength.toUpperCase()) {
      case 'STRONG':
        return 'text-purple-600 bg-purple-50 border-purple-200'
      case 'MEDIUM':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'WEAK':
        return 'text-gray-600 bg-gray-50 border-gray-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }



  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      {renderHeader()}

      {/* Signal Data */}
      <div className="grid md:grid-cols-2 gap-8 mb-8">
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
            Signal Details
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 font-medium">Action:</span>
              <span className={`px-3 py-2 rounded-full text-sm font-semibold border ${getActionColor(signal.signal_data.action)}`}>
                {signal.signal_data.action}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 font-medium">Strength:</span>
              <span className={`px-3 py-2 rounded-full text-sm font-semibold border ${getStrengthColor(signal.signal_data.strength)}`}>
                {signal.signal_data.strength}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 font-medium">Confidence:</span>
              <span className="font-bold text-lg text-gray-900">{signal.signal_data.confidence_score}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600 font-medium">Position Size:</span>
              <span className="font-bold text-lg text-blue-600">{(signal.signal_data.position_sizing * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <span className="w-2 h-2 bg-emerald-500 rounded-full mr-3"></span>
            Market Analysis
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600 font-medium">Market Regime:</span>
              <span className="font-medium text-gray-900">{signal.market_conditions.market_regime}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <span className="w-2 h-2 bg-purple-500 rounded-full mr-3"></span>
          Trading Recommendation
        </h3>
        <div className="space-y-4">
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <span className="text-blue-800 font-semibold">Action:</span>
            <span className="ml-2 text-blue-900 font-bold">{signal.recommendation.action}</span>
          </div>
          <div>
            <span className="text-gray-700 font-semibold">Analysis:</span>
            <p className="mt-2 text-gray-900 leading-relaxed">{signal.recommendation.reasoning}</p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <span className="text-gray-700 font-semibold">Portfolio Allocation:</span>
              <p className="mt-2 text-gray-900">{signal.recommendation.allocation_guidance}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <span className="text-gray-700 font-semibold">Execution Strategy:</span>
              <p className="mt-2 text-gray-900">{signal.recommendation.execution_strategy}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
