'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { supabase } from '@/lib/supabase'

interface OnboardingData {
  // Step 1: Basic Information
  country_residence: string
  investment_capital: number
  
  // Step 2: Trading Preferences
  trading_experience: string
  investment_goals: string
  
  // Step 3: Risk Assessment
  risk_tolerance: string
  time_horizon: string
}

export default function OnboardingPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [checkingUser, setCheckingUser] = useState(true)
  const [isNewUser, setIsNewUser] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [onboardingData, setOnboardingData] = useState<OnboardingData>({
    country_residence: 'US',
    investment_capital: 10000,
    trading_experience: 'beginner',
    investment_goals: 'long_term',
    risk_tolerance: 'moderate',
    time_horizon: '5_years'
  })

  useEffect(() => {
    if (loading) return

    if (!user) {
      router.push('/auth/signin')
      return
    }

    // Check if user already has a profile
    const checkUserProfile = async () => {
      try {
        const { data, error } = await supabase
          .from('user_profiles')
          .select('onboarding_completed')
          .eq('user_id', user.id)
          .single()

        if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
          console.error('Error checking user profile:', error)
          return
        }

        if (data?.onboarding_completed) {
          // User has completed onboarding, redirect to dashboard
          router.push('/dashboard')
        } else {
          // User exists but hasn't completed onboarding, or is completely new
          setIsNewUser(true)
          setCheckingUser(false)
        }
      } catch (error) {
        console.error('Error checking user profile:', error)
        // Assume new user if there's an error
        setIsNewUser(true)
        setCheckingUser(false)
      }
    }

    checkUserProfile()
  }, [user, loading, router])

  const handleInputChange = (field: keyof OnboardingData, value: string | number) => {
    setOnboardingData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const nextStep = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleCompleteOnboarding = async () => {
    if (!user?.id) {
      console.error('No user ID available')
      return
    }

    setIsSubmitting(true)
    console.log('Starting onboarding completion...', { userId: user.id, data: onboardingData })

    try {
      // Update existing user profile with onboarding data
      console.log('Updating user profile...')
      const { data: profileData, error: profileError } = await supabase
        .from('user_profiles')
        .update({
          onboarding_completed: true,
          country_residence: onboardingData.country_residence,
          investment_capital: onboardingData.investment_capital,
        })
        .eq('user_id', user.id)
        .select()

      if (profileError) {
        console.error('Error creating user profile:', profileError)
        alert('Failed to create user profile. Please try again.')
        setIsSubmitting(false)
        return
      }

      console.log('User profile updated successfully:', profileData)

      // Update existing portfolio with onboarding data
      console.log('Updating user portfolio...')
      const { data: portfolioData, error: portfolioError } = await supabase
        .from('user_portfolios')
        .update({
          total_value: onboardingData.investment_capital,
          cash_balance: onboardingData.investment_capital,
        })
        .eq('user_id', user.id)
        .select()

      if (portfolioError) {
        console.error('Error creating user portfolio:', portfolioError)
        alert('Failed to create user portfolio. Please try again.')
        setIsSubmitting(false)
        return
      }

      console.log('User portfolio updated successfully:', portfolioData)

      // Force refresh the auth context to update onboarding status
      console.log('Redirecting to dashboard...')
      
      // Refresh auth context to update onboarding status
      if (typeof window !== 'undefined') {
        // Force a page refresh to ensure auth context is updated
        window.location.href = '/dashboard'
      } else {
        router.push('/dashboard')
      }

    } catch (error) {
      console.error('Error completing onboarding:', error)
      alert('An unexpected error occurred. Please try again.')
      setIsSubmitting(false)
    }
  }

  if (loading || checkingUser) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Checking your account...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  if (!isNewUser) {
    return null
  }

  const renderStep1 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Where do you live?
        </label>
        <select
          value={onboardingData.country_residence}
          onChange={(e) => handleInputChange('country_residence', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="US">United States</option>
          <option value="CA">Canada</option>
          <option value="UK">United Kingdom</option>
          <option value="AU">Australia</option>
          <option value="DE">Germany</option>
          <option value="FR">France</option>
          <option value="JP">Japan</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          How much are you planning to invest initially?
        </label>
        <div className="relative">
          <span className="absolute left-3 top-2 text-gray-500">$</span>
          <input
            type="number"
            value={onboardingData.investment_capital}
            onChange={(e) => handleInputChange('investment_capital', parseInt(e.target.value) || 10000)}
            className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="10000"
            min="1000"
            step="1000"
          />
        </div>
        <p className="text-sm text-gray-500 mt-1">Minimum: $1,000</p>
      </div>
    </div>
  )

  const renderStep2 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What's your trading experience level?
        </label>
        <select
          value={onboardingData.trading_experience}
          onChange={(e) => handleInputChange('trading_experience', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="beginner">Beginner - New to trading</option>
          <option value="intermediate">Intermediate - Some experience</option>
          <option value="advanced">Advanced - Experienced trader</option>
          <option value="professional">Professional - Institutional level</option>
        </select>
      </div>



      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What are your primary investment goals?
        </label>
        <select
          value={onboardingData.investment_goals}
          onChange={(e) => handleInputChange('investment_goals', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="short_term">Short-term gains (1-12 months)</option>
          <option value="medium_term">Medium-term growth (1-5 years)</option>
          <option value="long_term">Long-term wealth building (5+ years)</option>
          <option value="income">Regular income generation</option>
        </select>
      </div>
    </div>
  )

  const renderStep3 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What's your risk tolerance?
        </label>
        <select
          value={onboardingData.risk_tolerance}
          onChange={(e) => handleInputChange('risk_tolerance', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="conservative">Conservative - Low risk, steady returns</option>
          <option value="moderate">Moderate - Balanced risk and return</option>
          <option value="aggressive">Aggressive - Higher risk, higher potential returns</option>
        </select>
      </div>



      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          What's your investment time horizon?
        </label>
        <select
          value={onboardingData.time_horizon}
          onChange={(e) => handleInputChange('time_horizon', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="1_year">1 year or less</option>
          <option value="3_years">1-3 years</option>
          <option value="5_years">3-5 years</option>
          <option value="10_years">5-10 years</option>
          <option value="10_plus">10+ years</option>
        </select>
      </div>

      {/* Summary of all selections */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-3">Summary of Your Preferences</h4>
        <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
          <div>Country: {onboardingData.country_residence}</div>
          <div>Investment: ${onboardingData.investment_capital.toLocaleString()}</div>
          <div>Experience: {onboardingData.trading_experience}</div>
          <div>Goals: {onboardingData.investment_goals.replace('_', ' ')}</div>
          <div>Risk: {onboardingData.risk_tolerance}</div>
          <div>Time Horizon: {onboardingData.time_horizon.replace('_', ' ')}</div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900">Welcome to QuantREX</h1>
            <span className="text-sm text-gray-500">Step {currentStep} of 3</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(currentStep / 3) * 100}%` }}
            ></div>
          </div>
          <div className="flex justify-between mt-2 text-sm text-gray-600">
            <span>Basic Information</span>
            <span>Trading Preferences</span>
            <span>Risk Assessment</span>
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-white shadow rounded-lg p-8">
          {currentStep === 1 && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-6">Basic Information</h2>
              <p className="text-gray-600 mb-6">Let's start with some basic details about you and your investment plans.</p>
              {renderStep1()}
            </div>
          )}

          {currentStep === 2 && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-6">Trading Preferences</h2>
              <p className="text-gray-600 mb-6">Tell us about your trading experience and preferences.</p>
              {renderStep2()}
            </div>
          )}

          {currentStep === 3 && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-6">Risk Assessment</h2>
              <p className="text-gray-600 mb-6">Help us understand your risk tolerance and investment timeline.</p>
              {renderStep3()}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8">
            <button
              onClick={prevStep}
              disabled={currentStep === 1}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                currentStep === 1
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Previous
            </button>

            <div className="flex space-x-3">
              {currentStep < 3 ? (
                <button
                  onClick={nextStep}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                >
                  Next
                </button>
              ) : (
                <button
                  onClick={handleCompleteOnboarding}
                  disabled={isSubmitting}
                  className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                    isSubmitting
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-700'
                  } text-white`}
                >
                  {isSubmitting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mx-auto"></div>
                      <span className="ml-2">Setting up...</span>
                    </>
                  ) : (
                    'Complete Setup & Go to Dashboard'
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
