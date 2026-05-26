import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, ScrollView, ActivityIndicator, Alert, StyleSheet } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import * as WebBrowser from 'expo-web-browser';
import * as SecureStore from 'expo-secure-store';
import { Check, ChevronRight, ExternalLink } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

WebBrowser.maybeCompleteAuthSession();

export default function AuthAuthorize() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const services = params.services ? String(params.services).split(',') : [];
  const [user, setUser] = useState<any>(null);
  const [authStatus, setAuthStatus] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthorizing, setIsAuthorizing] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      if (user) {
        checkAuthStatus(user.id);
      }
    });
  }, []);

  const checkAuthStatus = async (userId: string) => {
    try {
      const response = await axios.get(`${API_URL}/auth/status/${userId}`);
      const status = response.data.status || {};
      setAuthStatus(status);
    } catch (err) {
      console.error('Error checking auth status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAuthorize = async (service: string) => {
    if (!user) return;

    setIsAuthorizing(service);
    try {
      // Set OAuth in progress flag to prevent auto-logout
      await SecureStore.setItemAsync('oauth_in_progress', 'true');
      console.log('[AUTH] Set oauth_in_progress flag for', service);

      const response = await axios.get(`${API_URL}/auth/${service}`, {
        params: { user_id: user.id }
      });

      const { authorization_url } = response.data;

      // Open the authorization URL in a web browser with deep link redirect
      const result = await WebBrowser.openAuthSessionAsync(authorization_url, 'personaldatabasemobile://auth/callback');

      if (result.type === 'success') {
        // Refresh auth status
        await checkAuthStatus(user.id);
        Alert.alert('SUCCESS', `${service} authorized successfully`);
      } else if (result.type === 'cancel') {
        Alert.alert('CANCELLED', 'Authorization was cancelled');
      }
    } catch (error: any) {
      Alert.alert('ERROR', error.response?.data?.detail || 'Failed to initiate authorization');
    } finally {
      // Clear OAuth in progress flag
      await SecureStore.setItemAsync('oauth_in_progress', 'false');
      console.log('[AUTH] Cleared oauth_in_progress flag for', service);
      setIsAuthorizing(null);
    }
  };

  const handleContinue = () => {
    router.replace('/setup');
  };

  const allAuthorized = services.every(service => authStatus[service]);

  if (isLoading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#9333ea" />
      </View>
    );
  }

  const serviceNames: Record<string, string> = {
    calendar: 'Google Calendar',
    gmail: 'Gmail',
    google_drive: 'Google Drive',
    github: 'GitHub'
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Service Authorization</Text>
        <Text style={styles.subtitle}>
          Authorize the following services to enable data synchronization
        </Text>

        {services.map((service) => (
          <View key={service} style={styles.serviceCard}>
            <View style={styles.serviceInfo}>
              <Text style={styles.serviceName}>{serviceNames[service] || service}</Text>
              <Text style={styles.serviceStatus}>
                {authStatus[service] ? '✓ Authorized' : 'Not authorized'}
              </Text>
            </View>
            {authStatus[service] ? (
              <View style={styles.authorizedBadge}>
                <Check size={16} color="#10b981" />
              </View>
            ) : (
              <TouchableOpacity
                onPress={() => handleAuthorize(service)}
                disabled={isAuthorizing === service}
                style={styles.authorizeButton}
              >
                {isAuthorizing === service ? (
                  <ActivityIndicator size="small" color="#9333ea" />
                ) : (
                  <>
                    <Text style={styles.authorizeButtonText}>Authorize</Text>
                    <ExternalLink size={16} color="#9333ea" />
                  </>
                )}
              </TouchableOpacity>
            )}
          </View>
        ))}

        {allAuthorized && (
          <TouchableOpacity
            onPress={handleContinue}
            style={styles.continueButton}
          >
            <LinearGradient colors={['#7c3aed', '#4f46e5']} style={styles.buttonGradient}>
              <Text style={styles.buttonText}>Continue to Setup</Text>
              <ChevronRight size={20} color="white" />
            </LinearGradient>
          </TouchableOpacity>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  scrollContent: {
    padding: 32,
    paddingTop: 60,
  },
  title: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 8,
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: 14,
    marginBottom: 32,
    lineHeight: 20,
  },
  serviceCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  serviceInfo: {
    flex: 1,
  },
  serviceName: {
    color: '#e2e8f0',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  serviceStatus: {
    color: '#64748b',
    fontSize: 12,
  },
  authorizedBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  authorizeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
  },
  authorizeButtonText: {
    color: '#9333ea',
    fontSize: 14,
    fontWeight: '600',
    marginRight: 8,
  },
  continueButton: {
    marginTop: 24,
    shadowColor: '#6366f1',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
  },
  buttonGradient: {
    height: 64,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
    marginRight: 8,
  },
});
