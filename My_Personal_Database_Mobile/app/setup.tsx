import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Alert,
  StyleSheet,
  StatusBar,
  Linking,
} from 'react-native';
import { supabase } from '../lib/supabase';
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { LogOut } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import SetupProgress from '../components/setup/SetupProgress';
import SetupStep1 from '../components/setup/SetupStep1';
import SetupStep2 from '../components/setup/SetupStep2';
import SetupStep3 from '../components/setup/SetupStep3';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';

export default function SetupScreen() {
  const [user, setUser] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedProtocols, setSelectedProtocols] = useState<Record<string, boolean>>({
    appleNotes: true,
    appleCalendar: true,
    appleMusic: true,
    iosContacts: true,
    androidContacts: true,
    locationData: true,
    spotify: true,
    googleCalendar: true,
    gmail: true,
    googleDrive: true,
    github: true,
    zoom: true,
  });
  const router = useRouter();
  const fetchSetupRef = useRef<{ timeout: number | null; checked: boolean }>({ timeout: null, checked: false });
  const pollingIntervalsRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      if (user) {
        // Prevent repeated checks
        if (fetchSetupRef.current.checked) {
          return;
        }

        // Debounce: cancel previous pending call
        if (fetchSetupRef.current.timeout) {
          clearTimeout(fetchSetupRef.current.timeout);
        }

        fetchSetupRef.current.timeout = setTimeout(() => {
          // Fetch current setup step and start at appropriate step
          axios.get(`${API_URL}/user-settings/${user.id}`)
            .then(response => {
              const setupStep = response.data.setup_step || 1;
              if (setupStep >= 4) {
                // Setup complete, redirect to chat
                router.replace('/');
              } else {
                setCurrentStep(setupStep);
              }
            })
            .catch(err => {
              console.error('Error fetching setup status:', err);
              setCurrentStep(1);
            })
            .finally(() => {
              fetchSetupRef.current.timeout = null;
              fetchSetupRef.current.checked = true;
            });
        }, 500); // 500ms debounce
      }
    });

    return () => {
      if (fetchSetupRef.current.timeout) {
        clearTimeout(fetchSetupRef.current.timeout);
      }
      // Cleanup all polling intervals on unmount
      Object.values(pollingIntervalsRef.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervalsRef.current = {};
    };
  }, []);

  const handleCreateDatabase = async () => {
    setIsProcessing(true);
    try {
      await axios.post(`${API_URL}/create-user-database`, { user_id: user.id });
      setCurrentStep(2);
    } catch (error: any) {
      Alert.alert('INITIALIZATION ERROR', error.response?.data?.detail || 'Failed to create database');
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePermissions = () => {
    setCurrentStep(3);
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  };

  const toggleProtocol = (key: string) => {
    setSelectedProtocols(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleUpload = async () => {
    Alert.alert(
      'WARNING: DATA INGESTION',
      'Once enabled, data ingestion cannot be disabled without deleting all of your data from the database. Are you sure you want to proceed?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Proceed',
          style: 'destructive',
          onPress: async () => {
            setIsProcessing(true);
            try {
              // Check which services need OAuth authorization
              const oauthServices = [];
              if (selectedProtocols.googleCalendar) oauthServices.push('calendar');
              if (selectedProtocols.gmail) oauthServices.push('gmail');
              if (selectedProtocols.googleDrive) oauthServices.push('google_drive');
              if (selectedProtocols.github) oauthServices.push('github');
              if (selectedProtocols.zoom) oauthServices.push('zoom');

              // Check authorization status
              if (oauthServices.length > 0) {
                try {
                  const authStatus = await axios.get(`${API_URL}/auth/status/${user.id}`);
                  const status = authStatus.data.status || {};

                  const needsAuth = oauthServices.filter(service => !status[service]);

                  if (needsAuth.length > 0) {
                    // Authorize each service using polling
                    setIsProcessing(false);
                    
                    for (const service of needsAuth) {
                      const serviceName = service === 'calendar' ? 'Google Calendar' : service === 'gmail' ? 'Gmail' : service === 'google_drive' ? 'Google Drive' : service === 'github' ? 'GitHub' : service === 'zoom' ? 'Zoom' : service;
                      
                      Alert.alert(
                        `AUTHORIZATION REQUIRED - ${serviceName}`,
                        `You need to authorize ${serviceName}. You will be redirected to the authorization page.`,
                        [
                          {
                            text: 'Cancel',
                            style: 'cancel',
                            onPress: () => {
                              setIsProcessing(false);
                              return;
                            }
                          },
                          {
                            text: 'Authorize',
                            onPress: async () => {
                              setIsProcessing(true);

                              // Set OAuth in progress flag to prevent auto-logout
                              await SecureStore.setItemAsync('oauth_in_progress', 'true');
                              console.log('[SETUP] Set oauth_in_progress flag for', service);

                              // Get authorization URL
                              const authResponse = await axios.get(`${API_URL}/auth/${service}`, {
                                params: { user_id: user.id }
                              });

                              const { authorization_url } = authResponse.data;

                              // Open authorization URL in browser
                              const supported = await Linking.canOpenURL(authorization_url);
                              if (supported) {
                                await Linking.openURL(authorization_url);
                                
                                // Poll for authorization status with max attempts
                                let pollAttempts = 0;
                                const maxAttempts = 90; // 90 attempts * 2 seconds = 3 minutes max
                                
                                const pollInterval = setInterval(async () => {
                                  pollingIntervalsRef.current[service] = pollInterval;
                                  pollAttempts++;

                                  try {
                                    const statusResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
                                    const currentStatus = statusResponse.data.status || {};

                                    console.log(`[SETUP POLL] Attempt ${pollAttempts}/${maxAttempts}, service ${service} authorized:`, currentStatus[service]);

                                    if (currentStatus[service] || pollAttempts >= maxAttempts) {
                                      // Authorization complete or max attempts reached
                                      clearInterval(pollInterval);
                                      delete pollingIntervalsRef.current[service];

                                      // Clear OAuth in progress flag
                                      await SecureStore.setItemAsync('oauth_in_progress', 'false');
                                      console.log('[SETUP] Cleared oauth_in_progress flag for', service);

                                      if (currentStatus[service]) {
                                        // If this was the last service needing auth, proceed with upload
                                        const remainingServices = needsAuth.filter(s => s !== service);
                                        if (remainingServices.length === 0) {
                                          // All services authorized, proceed with upload
                                          const apiPermissions = {
                                            notes: selectedProtocols.appleNotes,
                                            appleCalendar: selectedProtocols.appleCalendar,
                                            appleMusic: selectedProtocols.appleMusic,
                                            iosContacts: selectedProtocols.iosContacts,
                                            androidContacts: selectedProtocols.androidContacts,
                                            locationData: selectedProtocols.locationData,
                                            calendar: selectedProtocols.googleCalendar,
                                            email: selectedProtocols.gmail,
                                            googleDrive: selectedProtocols.googleDrive,
                                            spotify: selectedProtocols.spotify,
                                            github: selectedProtocols.github,
                                            zoom: selectedProtocols.zoom,
                                          };

                                          await axios.post(`${API_URL}/upload-documents`, {
                                            user_id: user.id,
                                            permissions: apiPermissions
                                          });

                                          await axios.post(`${API_URL}/save-permissions`, {
                                            user_id: user.id,
                                            permissions: apiPermissions,
                                            setup_step: 4
                                          });

                                          // Set skip flag to prevent immediate setup check in layout
                                          // Use a global flag via localStorage to communicate with _layout.tsx
                                          try {
                                            localStorage.setItem('skipSetupCheckUntil', String(Date.now() + 10000)); // Skip for 10 seconds
                                          } catch (e) {
                                            console.warn('Could not set skip flag:', e);
                                          }

                                          router.replace('/');
                                        }
                                      } else {
                                        // Max attempts reached without authorization
                                        await SecureStore.setItemAsync('oauth_in_progress', 'false');
                                        console.log('[SETUP] Cleared oauth_in_progress flag on timeout for', service);
                                        setIsProcessing(false);
                                        Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
                                      }
                                    }
                                  } catch (err) {
                                    console.error('Error polling auth status:', err);
                                    if (pollAttempts >= maxAttempts) {
                                      clearInterval(pollInterval);
                                      delete pollingIntervalsRef.current[service];
                                      await SecureStore.setItemAsync('oauth_in_progress', 'false');
                                      console.log('[SETUP] Cleared oauth_in_progress flag on error for', service);
                                      setIsProcessing(false);
                                    }
                                  }
                                }, 2000); // Poll every 2 seconds
                              } else {
                                Alert.alert('ERROR', 'Cannot open the authorization URL');
                                setIsProcessing(false);
                              }
                            }
                          }
                        ]
                      );
                      return; // Return after first alert to handle one at a time
                    }
                    return;
                  }
                } catch (err) {
                  console.error('Error checking auth status:', err);
                  // Continue with upload anyway
                }
              }

              const apiPermissions = {
                notes: selectedProtocols.appleNotes,
                appleCalendar: selectedProtocols.appleCalendar,
                appleMusic: selectedProtocols.appleMusic,
                iosContacts: selectedProtocols.iosContacts,
                androidContacts: selectedProtocols.androidContacts,
                locationData: selectedProtocols.locationData,
                calendar: selectedProtocols.googleCalendar,
                email: selectedProtocols.gmail,
                googleDrive: selectedProtocols.googleDrive,
                spotify: selectedProtocols.spotify,
                github: selectedProtocols.github,
                zoom: selectedProtocols.zoom,
              };

              await axios.post(`${API_URL}/upload-documents`, {
                user_id: user.id,
                permissions: apiPermissions
              });

              // Update setup_step to 4 to mark setup as complete
              await axios.post(`${API_URL}/save-permissions`, {
                user_id: user.id,
                permissions: apiPermissions,
                setup_step: 4
              });

              // Set skip flag to prevent immediate setup check in layout
              try {
                localStorage.setItem('skipSetupCheckUntil', String(Date.now() + 10000)); // Skip for 10 seconds
              } catch (e) {
                console.warn('Could not set skip flag:', e);
              }

              router.replace('/');
            } catch (error: any) {
              Alert.alert('UPLOADING ERROR', error.response?.data?.detail || 'Failed to upload documents');
            } finally {
              setIsProcessing(false);
            }
          }
        }
      ]
    );
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient
        colors={['#0f172a', '#020617', '#000000']}
        style={StyleSheet.absoluteFill}
      />
      
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>INITIALIZATION</Text>
          <SetupProgress currentStep={currentStep} />
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent}>
          {currentStep === 1 && (
            <SetupStep1
              isProcessing={isProcessing}
              onCreateDatabase={handleCreateDatabase}
              onLogout={handleLogout}
            />
          )}

          {currentStep === 2 && (
            <SetupStep2
              selectedProtocols={selectedProtocols}
              onToggleProtocol={toggleProtocol}
              onBack={handleBack}
              onContinue={handlePermissions}
              onLogout={handleLogout}
            />
          )}

          {currentStep === 3 && (
            <SetupStep3
              selectedProtocols={selectedProtocols}
              isProcessing={isProcessing}
              onBack={handleBack}
              onUpload={handleUpload}
              onLogout={handleLogout}
            />
          )}
        </ScrollView>
        
        <View style={styles.footer}>
          <Text style={styles.footerText}>SECURE MAINFRAME INITIALIZATION V1.0</Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  safeArea: {
    flex: 1,
  },
  header: {
    paddingTop: 20,
    paddingHorizontal: 32,
    alignItems: 'center',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 4,
    marginBottom: 24,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 32,
  },
  footer: {
    padding: 24,
    alignItems: 'center',
  },
  footerText: {
    color: '#334155',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 3,
  },
});
