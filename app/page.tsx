'use client'

import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'
import LandingPage from '@/components/landing/LandingPage'

export default function HomePage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // Always show landing page, but add dashboard button for authenticated users
  return <LandingPage />
}
