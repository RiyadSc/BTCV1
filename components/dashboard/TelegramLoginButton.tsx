'use client'

import { useEffect, useRef } from 'react'

interface TelegramLoginButtonProps {
  botUsername: string
  onAuth: (user: any) => void
}

export default function TelegramLoginButton({ botUsername, onAuth }: TelegramLoginButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Set up global callback - using standard name from official Telegram embed
    ;(window as any).onTelegramAuth = (user: any) => {
      console.log('Telegram auth callback triggered:', user)
      onAuth(user)
    }

    // Create script element - matching official Telegram embed code exactly
    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botUsername)
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    script.setAttribute('data-request-access', 'write')

    // Append to container
    if (containerRef.current) {
      containerRef.current.innerHTML = '' // Clear any existing content
      containerRef.current.appendChild(script)
    }

    return () => {
      // Cleanup
      if (containerRef.current && containerRef.current.contains(script)) {
        containerRef.current.removeChild(script)
      }
      // Keep the callback available for subsequent mounts
    }
  }, [botUsername, onAuth])

  return <div ref={containerRef} className="flex justify-center" />
}

