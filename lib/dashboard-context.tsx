'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { useAuth } from './auth-context'

interface SignalData {
  action: string
  strength: string
  confidence_score: number
  position_sizing: number
  risk_cluster: string
}

interface MarketConditions {
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

interface Recommendation {
  action: string
  reasoning: string
  allocation_guidance: string
  execution_strategy: string
  risk_management: string
}

interface TradingSignal {
  signal_id: string
  timestamp: string
  signal_data: SignalData
  market_conditions: MarketConditions
  risk_assessment: {
    volatility_percentile: number
    drawdown_risk: number
    momentum_risk: string
    regime_stability: string
    overall_risk_score: number
  }
  recommendation: Recommendation
  is_previous_day?: boolean
  message?: string
}

interface MarketData {
  market_regime: string
  sentiment_index: number
  sentiment_classification: string
  price_momentum: {
    '7_day': number
    '30_day': number
  }
  volatility_index: number
  current_price: number
  price_change: number
  price_change_percent: number
  is_price_up: boolean
  is_price_down: boolean
  trend_direction: string
  timestamp: string
}

interface DashboardData {
  currentSignal: TradingSignal | null
  marketData: MarketData | null
  signalLoading: boolean
  signalError: string | null
  marketLoading: boolean
  marketError: string | null
  lastUpdated: Date | null
}

interface DashboardContextType {
  data: DashboardData
  loadMarketData: () => Promise<void>
  loadSignalData: () => Promise<void>
  refreshAll: () => Promise<void>
  clearData: () => void
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined)

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData>({
    currentSignal: null,
    marketData: null,
    signalLoading: false,
    signalError: null,
    marketLoading: false,
    marketError: null,
    lastUpdated: null
  })

  const loadMarketData = async () => {
    if (!user) return

    try {
      setData(prev => ({ ...prev, marketLoading: true, marketError: null }))
      
      // Fetch market overview from Supabase Edge Function (public endpoint)
      const marketResponse = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/get-market-overview`)

      if (!marketResponse.ok) {
        throw new Error('Failed to fetch market data')
      }

      const marketData = await marketResponse.json()
      
      setData(prev => ({
        ...prev,
        marketData,
        marketLoading: false,
        lastUpdated: new Date()
      }))
    } catch (err) {
      console.error('Market data error:', err)
      setData(prev => ({
        ...prev,
        marketError: 'Failed to load market data',
        marketLoading: false
      }))
    }
  }

  const loadSignalData = async () => {
    if (!user) return

    try {
      setData(prev => ({ ...prev, signalLoading: true, signalError: null }))
      
      // Fetch the current weekly signal from Supabase Edge Function (public endpoint)
      const signalResponse = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/get-daily-signal`, {
        headers: {
          'X-User-Join-Date': user.created_at
        }
      })

      if (!signalResponse.ok) {
        throw new Error('Failed to fetch weekly signal')
      }

      const signalData = await signalResponse.json()
      
      // Check if we got actual signal data or an error message
      if (signalData.message && signalData.message.includes('No signal')) {
        // No signal available today
        setData(prev => ({
          ...prev,
          currentSignal: null,
          signalLoading: false,
          lastUpdated: new Date()
        }))
      } else if (signalData.signal_data) {
        // We have a valid signal
        setData(prev => ({
          ...prev,
          currentSignal: signalData,
          signalLoading: false,
          lastUpdated: new Date()
        }))
      } else {
        // Unexpected response format
        throw new Error('Invalid signal data format')
      }
    } catch (err) {
      console.error('Signal data error:', err)
      setData(prev => ({
        ...prev,
        signalError: 'Failed to load weekly signal',
        signalLoading: false
      }))
    }
  }

  const refreshAll = async () => {
    await Promise.all([loadMarketData(), loadSignalData()])
  }

  const clearData = () => {
    setData({
      currentSignal: null,
      marketData: null,
      signalLoading: false,
      signalError: null,
      marketLoading: false,
      marketError: null,
      lastUpdated: null
    })
  }

  // Load data when user signs in
  useEffect(() => {
    if (user) {
      loadMarketData()
      loadSignalData()
    } else {
      clearData()
    }
  }, [user])

  // Refresh market data every 5 minutes
  useEffect(() => {
    if (user) {
      const interval = setInterval(() => {
        loadMarketData()
      }, 5 * 60 * 1000) // 5 minutes

      return () => clearInterval(interval)
    }
  }, [user])

  const value = {
    data,
    loadMarketData,
    loadSignalData,
    refreshAll,
    clearData
  }

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const context = useContext(DashboardContext)
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider')
  }
  return context
}
