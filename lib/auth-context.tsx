'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { createClient, User, AuthError } from '@supabase/supabase-js'
import { supabase } from './supabase'

interface AuthContextType {
  user: User | null
  loading: boolean
  onboardingCompleted: boolean
  membershipStatus: string | null
  signUp: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signInWithGoogle: () => Promise<{ error: AuthError | null }>
  signOut: () => Promise<void>
  resetPassword: (email: string) => Promise<{ error: AuthError | null }>
  checkOnboardingStatus: () => Promise<void>
  checkMembershipStatus: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [onboardingCompleted, setOnboardingCompleted] = useState(false)
  const [membershipStatus, setMembershipStatus] = useState<string | null>(null)

  const checkOnboardingStatus = async () => {
    if (!user) return
    
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('onboarding_completed')
        .eq('user_id', user.id)
        .single()

      if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
        console.error('Error checking onboarding status:', error)
        return
      }

      setOnboardingCompleted(data?.onboarding_completed || false)
    } catch (error) {
      console.error('Error checking onboarding status:', error)
    }
  }

  const checkMembershipStatus = async () => {
    if (!user) return
    
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('membership_status')
        .eq('user_id', user.id)
        .single()

      if (error && error.code !== 'PGRST116') { // PGRST116 = no rows returned
        console.error('Error checking membership status:', error)
        return
      }

      setMembershipStatus(data?.membership_status || 'free')
    } catch (error) {
      console.error('Error checking membership status:', error)
    }
  }

  useEffect(() => {
    // Get initial session
    const getInitialSession = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setUser(session?.user ?? null)
      setLoading(false)
    }

    getInitialSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setUser(session?.user ?? null)
        setLoading(false)
        
        // Check onboarding status when user changes
        if (session?.user) {
          await checkOnboardingStatus()
          await checkMembershipStatus()
        } else {
          setOnboardingCompleted(false)
          setMembershipStatus(null)
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  // Check onboarding status when user changes
  useEffect(() => {
    if (user) {
      checkOnboardingStatus()
      checkMembershipStatus()
    }
  }, [user])

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
    })
    return { error }
  }

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return { error }
  }

  const signInWithGoogle = async () => {
    // For Google OAuth, we'll redirect to membership review first
    // The membership review page will check status and redirect accordingly
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/membership-review`
      }
    })
    return { error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`
    })
    return { error }
  }

  const value = {
    user,
    loading,
    onboardingCompleted,
    membershipStatus,
    signUp,
    signIn,
    signInWithGoogle,
    signOut,
    resetPassword,
    checkOnboardingStatus,
    checkMembershipStatus,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
