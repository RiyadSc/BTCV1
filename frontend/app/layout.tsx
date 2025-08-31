import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '../lib/auth-context'
import { DashboardProvider } from '../lib/dashboard-context'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Quant Trading Bot - Professional Trading Signals',
  description: 'Get institutional-grade quantitative trading signals based on Fear & Greed Index analysis. Make data-driven decisions with confidence.',
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
