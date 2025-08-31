'use client'

import React, { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function MembershipReviewPage() {
  const { user, membershipStatus, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && user) {
      // If user has paid membership, redirect to dashboard
      if (membershipStatus === 'paid') {
        router.push('/dashboard')
        return
      }
      
      // If user has completed onboarding, redirect to dashboard
      // (This handles existing users who might not have membership_status set)
      if (membershipStatus === null) {
        router.push('/onboarding')
        return
      }
    }
  }, [user, membershipStatus, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  // Only show this page for users with 'free' membership status
  if (membershipStatus !== 'free') {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Navigation Header */}
      <nav className="relative z-10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center">
            <Link 
              href="/"
              className="flex items-center text-white hover:text-blue-300 transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Go back
            </Link>
          </div>
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-white">QuantREX</h1>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          {/* Status Icon */}
          <div className="w-24 h-24 bg-amber-500 rounded-full flex items-center justify-center mx-auto mb-8">
            <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>

          {/* Main Message */}
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Membership Under Review
          </h1>
          
          <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
            Thank you for joining QuantREX! Your account is currently being reviewed for premium access.
          </p>

          {/* Status Details */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 max-w-2xl mx-auto mb-8">
            <h2 className="text-2xl font-semibold text-white mb-4">What happens next?</h2>
            <div className="space-y-4 text-left">
              <div className="flex items-start">
                <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center mr-3 mt-1 flex-shrink-0">
                  <span className="text-white text-sm font-bold">1</span>
                </div>
                <p className="text-gray-300">Send 1 ETH to our wallet address for premium access</p>
              </div>
              <div className="flex items-start">
                <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center mr-3 mt-1 flex-shrink-0">
                  <span className="text-white text-sm font-bold">2</span>
                </div>
                <p className="text-gray-300">We'll verify your payment and approve your account</p>
              </div>
              <div className="flex items-start">
                <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center mr-3 mt-1 flex-shrink-0">
                  <span className="text-white text-sm font-bold">3</span>
                </div>
                <p className="text-gray-300">You'll receive immediate access to our trading signals and dashboard</p>
              </div>
            </div>
          </div>

          {/* Contact Info */}
          <div className="text-gray-400">
            <p className="mb-2">Questions? Contact us on telegram at @Rssss00000</p>
            <p className="text-sm">Please include your gmail address, your crypto address used for payment and the transaction hash (txid) for faster processing.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
