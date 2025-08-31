'use client'

import React from 'react'
import Link from 'next/link'

export default function LandingPage() {
  const handleGoogleSignIn = async () => {
    // Redirect to Google OAuth
    window.location.href = '/auth/signin'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
      {/* Navigation */}
      <nav className="relative z-10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-white">QuantREX</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Link 
              href="/auth/signin"
              className="text-white hover:text-blue-300 transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/auth/signup"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            Entropy-Adjusted
            <span className="text-blue-400"> Momentum Strategy</span>
            <br />
            with Advanced Risk Management
          </h1>
          <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
            Our quantitative trading bot delivers institutional-grade performance with proven backtest results. 
            Experience 703% total returns with sophisticated risk management.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <button
              onClick={handleGoogleSignIn}
              className="bg-white hover:bg-gray-100 text-gray-900 px-8 py-4 rounded-lg text-lg font-semibold transition-colors flex items-center justify-center"
            >
              <svg className="w-6 h-6 mr-3" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>
          </div>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link 
              href="/pricing"
              className="border border-white text-white hover:bg-white hover:text-gray-900 px-8 py-4 rounded-lg text-lg font-semibold transition-colors"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </div>

      {/* Performance Metrics Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            Proven Performance Results
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="text-4xl font-bold text-emerald-400 mb-2">703%</div>
              <div className="text-gray-300 text-sm">Total Return</div>
              <div className="text-emerald-400 text-xs mt-1">vs 656% Buy & Hold</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="text-4xl font-bold text-blue-400 mb-2">34.73%</div>
              <div className="text-gray-300 text-sm">Annual Return</div>
              <div className="text-blue-400 text-xs mt-1">Consistent Performance</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="text-4xl font-bold text-amber-400 mb-2">0.73</div>
              <div className="text-gray-300 text-sm">Sharpe Ratio</div>
              <div className="text-amber-400 text-xs mt-1">Risk-Adjusted Returns</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="text-4xl font-bold text-red-400 mb-2">65%</div>
              <div className="text-gray-300 text-sm">Win Rate</div>
              <div className="text-red-400 text-xs mt-1">194 Total Trades</div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Chart Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            Performance Visualization
          </h2>
          <div className="flex justify-center">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 max-w-4xl">
              <img 
                src="/performance-chart.png" 
                alt="Entropy-Adjusted Momentum Strategy Performance vs Buy & Hold BTC"
                className="w-full h-auto rounded-lg shadow-2xl"
              />
              <p className="text-gray-300 text-center mt-4 text-sm">
                Performance comparison showing our strategy's risk-adjusted returns vs traditional buy & hold approach
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">
            Advanced Strategy Features
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Entropy-Adjusted Analysis</h3>
              <p className="text-gray-400">
                Advanced algorithms that adapt to market conditions using entropy-based momentum signals and regime detection.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Real-Time Risk Management</h3>
              <p className="text-gray-400">
                Dynamic position sizing and drawdown protection with advanced risk management during extreme volatility.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">Proven Backtest Results</h3>
              <p className="text-gray-400">
                Comprehensive backtesting from 2018-2025 showing consistent outperformance vs buy & hold with $7,031.86 total P&L.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-blue-400 mb-2">$8,031</div>
              <div className="text-gray-300">Final Portfolio Value</div>
              <div className="text-blue-400 text-xs mt-1">From $1,000 Starting Capital</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-blue-400 mb-2">+47.19%</div>
              <div className="text-gray-300">Excess Return</div>
              <div className="text-blue-400 text-xs mt-1">vs Buy & Hold BTC</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-blue-400 mb-2">194</div>
              <div className="text-gray-300">Total Trades</div>
              <div className="text-blue-400 text-xs mt-1">77 Buy, 117 Sell</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-blue-400 mb-2">7+ Years</div>
              <div className="text-gray-300">Backtest Period</div>
              <div className="text-blue-400 text-xs mt-1">2018-2025 Data</div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative z-10 px-6 py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to Experience Professional-Grade Returns?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Join traders who trust our entropy-adjusted momentum strategy for superior risk-adjusted performance.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {user ? (
              <Link
                href="/dashboard"
                className="bg-white hover:bg-gray-100 text-gray-900 px-8 py-4 rounded-lg text-lg font-semibold transition-colors inline-block"
              >
                Go to Dashboard
              </Link>
            ) : (
              <>
                <button
                  onClick={handleGoogleSignIn}
                  className="bg-white hover:bg-gray-100 text-gray-900 px-8 py-4 rounded-lg text-lg font-semibold transition-colors flex items-center justify-center"
                >
                  <svg className="w-6 h-6 mr-3" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Start with Google
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Trading Disclaimer */}
      <div className="relative z-10 px-6 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-white mb-2">Important Trading Disclaimer</h3>
            <p className="text-white/80 text-xs leading-relaxed">
              <strong>Past performance does not guarantee future results.</strong> Cryptocurrency trading involves substantial risk of loss and is not suitable for all investors. 
              The value of cryptocurrencies can go down as well as up, and you may lose some or all of your investment. 
              Our trading signals are for informational purposes only and should not be considered as financial advice. 
              Always conduct your own research and consult with a qualified financial advisor before making investment decisions. 
              Never invest more than you can afford to lose.
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 px-6 py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-white font-semibold mb-4">QuantREX</h3>
              <p className="text-gray-400 text-sm">
                Entropy-Adjusted Momentum Strategy with Advanced Risk Management.
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/pricing" className="text-gray-400 hover:text-white">Pricing</Link></li>
                <li><Link href="/features" className="text-gray-400 hover:text-white">Features</Link></li>
                <li><Link href="/demo" className="text-gray-400 hover:text-white">Demo</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/about" className="text-gray-400 hover:text-white">About</Link></li>
                <li><Link href="/contact" className="text-gray-400 hover:text-white">Contact</Link></li>
                <li><Link href="/careers" className="text-gray-400 hover:text-white">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link href="/privacy" className="text-gray-400 hover:text-white">Privacy Policy</Link></li>
                <li><Link href="/terms" className="text-gray-400 hover:text-white">Terms of Service</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-gray-800 text-center">
            <p className="text-gray-400 text-sm">
              © 2024 QuantREX. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
