'use client'

import { useEffect } from 'react'
import { useAuth } from '@/lib/auth-context'
import { useDashboard } from '@/lib/dashboard-context'
import { useRouter } from 'next/navigation'
import DashboardLayout from '@/components/dashboard/DashboardLayout'
import SignalCard from '@/components/dashboard/SignalCard'
import LivePriceDisplay from '@/components/dashboard/LivePriceDisplay'
import SignalHistory from '@/components/dashboard/SignalHistory'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

export default function DashboardPage() {
  const { user, loading: authLoading, onboardingCompleted, membershipStatus } = useAuth()
  const { data, loadMarketData, loadSignalData } = useDashboard()
  const router = useRouter()

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth/signin')
      return
    }

    // Redirect to membership review if user has free membership
    if (!authLoading && user && membershipStatus === 'free') {
      router.push('/membership-review')
      return
    }

    // Redirect to onboarding if user hasn't completed it
    if (!authLoading && user && onboardingCompleted === false) {
      router.push('/onboarding')
      return
    }
  }, [user, authLoading, onboardingCompleted, membershipStatus, router])

  if (authLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      </DashboardLayout>
    )
  }

  if (!user) {
    return null
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Welcome Header */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-6 text-white">
          <h1 className="text-2xl font-bold mb-2 text-white">
            Welcome back, {user?.email?.split('@')[0]}
          </h1>
          <p className="text-white">
            Your quantitative trading intelligence center
          </p>
        </div>

        {/* Live BTC Price Display */}
        <LivePriceDisplay />

        {/* Main Content Grid */}
        <div className="grid lg:grid-cols-1 gap-6">
          {/* Signal Card */}
          <div className="lg:col-span-1">
            {data.currentSignal && (
              <SignalCard signal={data.currentSignal} />
            )}
            {!data.currentSignal && !data.signalLoading && !data.signalError && (
              <div className="card">
                <div className="text-center py-8">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    No Signal Available Today
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Daily trading signals are generated automatically. Check back later for today's signal.
                  </p>
                  <button 
                    onClick={loadSignalData}
                    className="btn-primary"
                  >
                    Refresh Signal
                  </button>
                </div>
              </div>
            )}
            {data.signalLoading && (
              <div className="card">
                <div className="flex items-center justify-center py-8">
                  <LoadingSpinner size="lg" />
                  <span className="ml-3 text-gray-600">Generating trading signal...</span>
                </div>
              </div>
            )}
            {data.signalError && (
              <div className="card border-danger-200 bg-danger-50">
                <div className="text-center py-6">
                  <div className="text-danger-600 mb-4">{data.signalError}</div>
                  <button 
                    onClick={loadSignalData}
                    className="btn-primary"
                  >
                    Retry Signal Generation
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Signal History */}
          <div className="lg:col-span-1">
            <SignalHistory />
          </div>
        </div>

        {/* Last Updated Info */}
        {data.lastUpdated && (
          <div className="text-center text-sm text-gray-500">
            Last updated: {data.lastUpdated.toLocaleTimeString()}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
