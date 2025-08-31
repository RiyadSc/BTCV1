import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/lib/auth-context'
import { DashboardProvider } from '@/lib/dashboard-context'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'QuantREX - Entropy-Adjusted Momentum Strategy',
  description: 'Professional quantitative trading signals powered by our proprietary Entropy-Adjusted Momentum Strategy. Institutional-grade risk management and data-driven returns.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <DashboardProvider>
            {children}
          </DashboardProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
