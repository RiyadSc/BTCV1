'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import TelegramLoginButton from './TelegramLoginButton'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { user, signOut } = useAuth()
  const router = useRouter()
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [telegramLinked, setTelegramLinked] = useState(false)
  const [showTelegramModal, setShowTelegramModal] = useState(false)
  const [linking, setLinking] = useState(false)

  useEffect(() => {
    if (user) {
      checkTelegramLink()
    }
  }, [user])

  const checkTelegramLink = async () => {
    try {
      const { data, error } = await supabase
        .from('telegram_users')
        .select('telegram_id')
        .eq('user_id', user?.id)
        .eq('is_active', true)
        .single()

      if (error && error.code !== 'PGRST116') {
        console.error('Error checking telegram link:', error)
      }

      setTelegramLinked(!!data)
    } catch (err) {
      console.error('Error checking telegram link:', err)
    }
  }

  const handleTelegramLogin = async (telegramAuth: any) => {
    try {
      setLinking(true)
      console.log('Telegram auth data received:', telegramAuth)

      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session) {
        throw new Error('Not authenticated')
      }

      console.log('Sending link request to edge function...')
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/link-telegram`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}`
          },
          body: JSON.stringify({ telegramAuth })
        }
      )

      const result = await response.json()
      console.log('Link response:', result)

      if (!response.ok) {
        throw new Error(result.error || 'Failed to link Telegram account')
      }

      // Refresh the telegram link status
      await checkTelegramLink()
      setShowTelegramModal(false)

      alert('✅ Telegram account linked successfully! You can now receive daily signals.')
    } catch (err: any) {
      console.error('Error linking Telegram:', err)
      alert(`❌ Failed to link Telegram: ${err.message}`)
    } finally {
      setLinking(false)
    }
  }

  const handleSignOut = async () => {
    try {
      await signOut()
      router.push('/')
    } catch (error) {
      console.error('Sign out failed:', error)
    }
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/dashboard" className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900">QuantREX</h1>
              </Link>
              

            </div>

            {/* Telegram Link Button & User Menu */}
            <div className="flex items-center gap-4">
              {/* Telegram Link Button */}
              <button
                onClick={() => telegramLinked ? null : setShowTelegramModal(true)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  telegramLinked 
                    ? 'bg-green-50 text-green-700 cursor-default' 
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.008-1.252-.241-1.865-.44-.752-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635.099-.002.321.023.465.141.121.099.155.232.171.325.016.093.036.305.02.469z"/>
                </svg>
                {telegramLinked ? (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Telegram Linked</span>
                  </>
                ) : (
                  <span>Link Telegram</span>
                )}
              </button>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user.email?.charAt(0).toUpperCase() || 'U'}
                    </span>
                  </div>
                  <span className="ml-2 text-gray-700 hidden md:block">{user.email}</span>
                  <svg className="ml-1 h-4 w-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>

                {isUserMenuOpen && (
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1">
                      <button
                        onClick={handleSignOut}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-500">
              © 2025 QuantREX. All rights reserved.
            </div>
            <div className="flex space-x-6">
              <Link href="/privacy" className="text-sm text-gray-500 hover:text-gray-700">
                Privacy Policy
              </Link>
              <Link href="/terms" className="text-sm text-gray-500 hover:text-gray-700">
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </footer>

      {/* Telegram Link Modal */}
      {showTelegramModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setShowTelegramModal(false)}
        >
          <div 
            className="bg-white rounded-lg p-6 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Link Telegram Account</h3>
              <button
                onClick={() => setShowTelegramModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <p className="text-sm text-gray-600 mb-6">
              Link your Telegram account to receive daily trading signals directly on Telegram.
            </p>

            <div className="flex flex-col items-center gap-4 py-6">
              {!linking && process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ? (
                <TelegramLoginButton
                  botUsername={process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME}
                  onAuth={handleTelegramLogin}
                />
              ) : !linking ? (
                <div className="text-center text-red-600 text-sm">
                  ⚠️ Telegram bot not configured. Please add NEXT_PUBLIC_TELEGRAM_BOT_USERNAME to your .env.local file.
                </div>
              ) : null}

              {linking && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span>Linking your account...</span>
                </div>
              )}
            </div>

            <p className="text-xs text-gray-500 text-center mt-4">
              By linking your Telegram account, you authorize QuantREX to send you trading signals and notifications.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
