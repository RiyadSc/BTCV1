'use client'

import React, { useEffect, useState } from 'react'

interface PriceData {
  price: number
  change: number
  changePercent: number
  isUp: boolean
  isDown: boolean
}

export default function LivePriceDisplay() {
  const [priceData, setPriceData] = useState<PriceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [wsConnected, setWsConnected] = useState(false)

  useEffect(() => {
    let ws: WebSocket | null = null
    let fallbackInterval: NodeJS.Timeout | null = null

    const connectWebSocket = () => {
      try {
        ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@ticker')
        
        ws.onopen = () => {
          console.log('WebSocket connected to Binance')
          setWsConnected(true)
          setError(null)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.c) { // Close price
              const currentPrice = parseFloat(data.c)
              // Use Binance's calculated values directly
              const priceChange = parseFloat(data.P) // 24h price change
              const priceChangePercent = parseFloat(data.P) // 24h price change percent
              
              // Validate the data
              if (isNaN(currentPrice) || isNaN(priceChange) || isNaN(priceChangePercent)) {
                console.warn('Invalid WebSocket data, skipping update')
                return
              }

              setPriceData({
                price: currentPrice,
                change: priceChange,
                changePercent: priceChangePercent,
                isUp: priceChange > 0,
                isDown: priceChange < 0
              })
              setLoading(false)
            }
          } catch (parseError) {
            console.error('Failed to parse WebSocket data:', parseError)
          }
        }

        ws.onerror = (event) => {
          console.error('WebSocket error:', event)
          setError('WebSocket connection error')
          setWsConnected(false)
        }

        ws.onclose = () => {
          console.log('WebSocket disconnected')
          setWsConnected(false)
          // Fallback to REST API
          startFallbackAPI()
        }
      } catch (error) {
        console.error('WebSocket connection failed:', error)
        setError('WebSocket connection failed')
        startFallbackAPI()
      }
    }

    const startFallbackAPI = () => {
      if (fallbackInterval) return
      
      fallbackInterval = setInterval(async () => {
        try {
          const response = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
          if (response.ok) {
            const data = await response.json()
            const currentPrice = parseFloat(data.lastPrice)
            const priceChange = parseFloat(data.priceChange) // 24h price change
            const priceChangePercent = parseFloat(data.priceChangePercent) // 24h price change percent
            
            // Validate the data
            if (isNaN(currentPrice) || isNaN(priceChange) || isNaN(priceChangePercent)) {
              console.warn('Invalid API data, skipping update')
              return
            }

            setPriceData({
              price: currentPrice,
              change: priceChange,
              changePercent: priceChangePercent,
              isUp: priceChange > 0,
              isDown: priceChange < 0
            })
            setLoading(false)
            setError(null)
          }
        } catch (apiError) {
          console.error('API fallback failed:', apiError)
          setError('Failed to fetch price data')
        }
      }, 5000) // Update every 5 seconds
    }

    // Initial connection
    connectWebSocket()

    // Cleanup
    return () => {
      if (ws) {
        ws.close()
      }
      if (fallbackInterval) {
        clearInterval(fallbackInterval)
      }
    }
  }, [])

  if (loading && !priceData) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading market data...</span>
        </div>
      </div>
    )
  }

  if (error && !priceData) {
    return (
      <div className="rounded-xl shadow-sm border border-red-200 bg-red-50 p-6">
        <div className="text-center py-6">
          <div className="text-red-600 mb-2 font-medium">Failed to load market data</div>
          <div className="text-sm text-red-500">{error}</div>
        </div>
      </div>
    )
  }

  if (!priceData) {
    return null
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-gray-900">Bitcoin (BTC)</h3>
          <div className="flex items-center space-x-2 mt-2">
            <span className="text-sm text-gray-500">Real-time Market Data</span>
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
            <span className="text-xs text-gray-400 font-medium">
              {wsConnected ? 'Live' : 'API'}
            </span>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-3xl font-bold text-gray-900">
            ${priceData.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className={`flex items-center space-x-2 mt-2 ${priceData.isUp ? 'text-emerald-600' : priceData.isDown ? 'text-red-600' : 'text-gray-600'}`}>
            <span className={`text-lg ${priceData.isUp ? 'text-emerald-600' : priceData.isDown ? 'text-red-600' : 'text-gray-600'}`}>
              {priceData.isUp ? '↗' : priceData.isDown ? '↘' : '→'}
            </span>
            <span className="font-semibold text-lg">
              ${Math.abs(priceData.change).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className="text-sm font-medium bg-gray-100 px-2 py-1 rounded-full">
              {priceData.isUp ? '+' : ''}{priceData.changePercent.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
