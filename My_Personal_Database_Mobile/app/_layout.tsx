import { Stack, useRouter, useSegments } from 'expo-router';
import { useEffect, useState, useRef } from 'react';
import * as SecureStore from 'expo-secure-store';
import { supabase } from '../lib/supabase';
import { Session } from '@supabase/supabase-js';
import { View, ActivityIndicator, AppState } from 'react-native';
import { ThemeProvider, DarkTheme, DefaultTheme } from '@react-navigation/native';
import { useColorScheme } from '@/components/useColorScheme';
import axios from 'axios';
import { useCache } from '../hooks/useCache';
import memoryManager from '../lib/memoryManager';
import '../global.css';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export default function RootLayout() {
  const [session, setSession] = useState<Session | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [setupStep, setSetupStep] = useState<number | null>(null);
  const segments = useSegments();
  const router = useRouter();
  const colorScheme = useColorScheme();
  const checkSetupRef = useRef<{ userId: string | null; timeout: number | null; checked: boolean; lastCheckTime: number; skipNextCheck: boolean; skipUntil: number }>({ userId: null, timeout: null, checked: false, lastCheckTime: 0, skipNextCheck: false, skipUntil: 0 });

  useEffect(() => {
    // Initialize memory manager
    memoryManager.initialize({
      maxMemoryUsage: 50, // 50MB for mobile
      cleanupInterval: 120000, // 2 minutes
      backgroundCleanupDelay: 3000, // 3 seconds
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) {
        checkSetupStatus(session.user.id);
      } else {
        setInitialized(true);
      }
    });

    supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      // Reset checked flag when session changes to allow re-check
      checkSetupRef.current.checked = false;
      // Set skip flag to prevent immediate check after auth state change
      checkSetupRef.current.skipNextCheck = true;
      if (session) {
        checkSetupStatus(session.user.id);
      } else {
        setSetupStep(null);
      }
    });

    // Cleanup memory manager on unmount
    return () => {
      memoryManager.cleanup();
    };
  }, []);

  const fetchUserSettings = async (userId: string): Promise<number> => {
    const response = await axios.get(`${API_URL}/user-settings/${userId}`);
    return response.data.setup_step || 1;
  };

  const checkSetupStatus = async (userId: string) => {
    // Check localStorage for skip flag set by setup screen
    try {
      const skipUntilStr = localStorage.getItem('skipSetupCheckUntil');
      if (skipUntilStr) {
        const skipUntil = parseInt(skipUntilStr, 10);
        const now = Date.now();
        if (now < skipUntil) {
          checkSetupRef.current.skipUntil = skipUntil;
          // Clear the flag if it's expired
          if (now >= skipUntil) {
            localStorage.removeItem('skipSetupCheckUntil');
          }
          return;
        } else {
          // Flag expired, remove it
          localStorage.removeItem('skipSetupCheckUntil');
        }
      }
    } catch (e) {
      console.warn('Could not read skip flag from localStorage:', e);
    }

    // Skip if flag is set (after data upload)
    if (checkSetupRef.current.skipNextCheck) {
      checkSetupRef.current.skipNextCheck = false;
      return;
    }

    // Skip if within skip period (after setup completion)
    const now = Date.now();
    if (now < checkSetupRef.current.skipUntil) {
      return;
    }

    // Prevent rapid repeated checks (minimum 5 seconds between checks)
    if (now - checkSetupRef.current.lastCheckTime < 5000) {
      return;
    }

    // Prevent repeated checks for same user
    if (checkSetupRef.current.userId === userId && checkSetupRef.current.checked) {
      return;
    }

    // Debounce: if same user, cancel previous pending call
    if (checkSetupRef.current.userId === userId && checkSetupRef.current.timeout) {
      clearTimeout(checkSetupRef.current.timeout);
    }

    checkSetupRef.current.userId = userId;

    checkSetupRef.current.timeout = setTimeout(async () => {
      try {
        const setupStepValue = await fetchUserSettings(userId);
        setSetupStep(setupStepValue);
        checkSetupRef.current.checked = true;
        checkSetupRef.current.lastCheckTime = Date.now();
      } catch (err) {
        console.error('Error checking setup status:', err);
        setSetupStep(1);
      } finally {
        setInitialized(true);
        checkSetupRef.current.timeout = null;
      }
    }, 500); // 500ms debounce (increased from 100ms)
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (checkSetupRef.current.timeout) {
        clearTimeout(checkSetupRef.current.timeout);
      }
    };
  }, []);

  // Auto-logout when app goes to background (disabled during OAuth)
  useEffect(() => {
    const subscription = AppState.addEventListener('change', async (nextAppState) => {
      if (nextAppState === 'background' || nextAppState === 'inactive') {
        // Check if OAuth is in progress by checking for polling intervals
        const isOAuthInProgress = await SecureStore.getItemAsync('oauth_in_progress') === 'true';
        if (!isOAuthInProgress) {
          console.log('[AUTH] App going to background, logging out user');
          supabase.auth.signOut();
        } else {
          console.log('[AUTH] OAuth in progress, skipping logout');
        }
      }
    });

    return () => {
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    if (!initialized) return;

    const inAuthGroup = segments[0] === 'login';
    const inSetupGroup = segments[0] === 'setup';

    if (!session) {
      if (!inAuthGroup) {
        router.replace('/login');
      }
    } else {
      if (setupStep !== null && setupStep < 4) {
        if (!inSetupGroup) {
          router.replace('/setup');
        }
      } else if (inAuthGroup || inSetupGroup) {
        router.replace('/');
      }
    }
  }, [session, segments, initialized, setupStep]);

  if (!initialized) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' }}>
        <ActivityIndicator size="large" color="#9333ea" />
      </View>
    );
  }

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="setup" options={{ headerShown: false }} />
        <Stack.Screen name="auth/callback" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
      </Stack>
    </ThemeProvider>
  );
}
