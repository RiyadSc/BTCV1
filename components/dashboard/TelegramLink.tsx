'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth-context'
import { supabase } from '@/lib/supabase'

interface TelegramUser {
  telegram_id: number
  telegram_username: string | null
  telegram_first_name: string | null
  is_active: boolean
  notification_enabled: boolean
  linked_at: string
}

export default function TelegramLink() {
  const { user } = useAuth()
  const [telegramUser, setTelegramUser] = useState<TelegramUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [linking, setLinking] = useState(false)

  useEffect(() => {
    if (user) {
      fetchTelegramLink()
    }
  }, [user])

  const fetchTelegramLink = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('telegram_users')
        .select('*')
        .eq('user_id', user?.id)
        .eq('is_active', true)
        .single()

      if (error && error.code !== 'PGRST116') {
        throw error
      }

      setTelegramUser(data)
    } catch (err: any) {
      console.error('Error fetching telegram link:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTelegramLogin = async (telegramAuth: any) => {
    try {
      setLinking(true)
      setError(null)

      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session) {
        throw new Error('Not authenticated')
      }

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

      if (!response.ok) {
        throw new Error(result.error || 'Failed to link Telegram account')
      }

      // Refresh the telegram link
      await fetchTelegramLink()

      alert('✅ Telegram account linked successfully! You can now receive weekly signals.')
    } catch (err: any) {
      console.error('Error linking Telegram:', err)
      setError(err.message)
      alert(`❌ Failed to link Telegram: ${err.message}`)
    } finally {
      setLinking(false)
    }
  }

  const handleUnlink = async () => {
    if (!confirm('Are you sure you want to unlink your Telegram account?')) {
      return
    }

    try {
      setLinking(true)
      const { error } = await supabase
        .from('telegram_users')
        .delete()
        .eq('user_id', user?.id)

      if (error) throw error

      setTelegramUser(null)
      alert('✅ Telegram account unlinked successfully')
    } catch (err: any) {
      console.error('Error unlinking Telegram:', err)
      setError(err.message)
      alert(`❌ Failed to unlink: ${err.message}`)
    } finally {
      setLinking(false)
    }
  }

  useEffect(() => {
    // Load Telegram Login Widget script
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    document.body.appendChild(script)

    // Create global callback for Telegram widget
    ;(window as any).onTelegramAuth = handleTelegramLogin

    return () => {
      document.body.removeChild(script)
      delete (window as any).onTelegramAuth
    }
  }, [])

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <svg className="w-8 h-8 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.008-1.252-.241-1.865-.44-.752-.244-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635.099-.002.321.023.465.141.121.099.155.232.171.325.016.093.036.305.02.469z"/>
          </svg>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Telegram Notifications</h3>
            <p className="text-sm text-gray-600">Receive weekly signals on Telegram</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {telegramUser ? (
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="font-semibold text-green-900">Telegram Connected</span>
                </div>
                <div className="text-sm text-green-800 space-y-1">
                  {telegramUser.telegram_first_name && (
                    <p>Name: {telegramUser.telegram_first_name}</p>
                  )}
                  {telegramUser.telegram_username && (
                    <p>Username: @{telegramUser.telegram_username}</p>
                  )}
                  <p>Linked: {new Date(telegramUser.linked_at).toLocaleDateString()}</p>
                  <p>Notifications: {telegramUser.notification_enabled ? '✅ Enabled' : '❌ Disabled'}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleUnlink}
              disabled={linking}
              className="px-4 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
            >
              {linking ? 'Unlinking...' : 'Unlink Telegram'}
            </button>
            <a
              href={`https://t.me/${process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              Open Bot
            </a>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900 mb-3">
              📱 Link your Telegram account to receive weekly trading signals directly on Telegram!
            </p>
            <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
              <li>Get instant notifications every Sunday for the new weekly signal</li>
              <li>Access signals via bot commands</li>
              <li>Never miss a trading opportunity</li>
            </ul>
          </div>

          <div className="flex flex-col items-center gap-4 py-4">
            <script 
              async 
              src="https://telegram.org/js/telegram-widget.js?22" 
              data-telegram-login={process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME}
              data-size="large"
              data-onauth="onTelegramAuth(user)"
              data-request-access="write"
            ></script>
            
            {linking && (
              <div className="text-sm text-gray-600">
                Linking your account...
              </div>
            )}

            <p className="text-xs text-gray-500 text-center max-w-md">
              By linking your Telegram account, you authorize QuantREX to send you trading signals and notifications.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

