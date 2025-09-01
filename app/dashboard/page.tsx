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
            <SignalCard 
              signal={data.currentSignal} 
              signalLoading={data.signalLoading}
              signalError={data.signalError}
              onRefresh={loadSignalData}
            />
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
