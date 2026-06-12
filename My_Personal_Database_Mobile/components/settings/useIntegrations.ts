import { useState, useEffect, useRef, useCallback } from 'react';
import { useFocusEffect, useRouter, useLocalSearchParams } from 'expo-router';
import * as Location from 'expo-location';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert, Platform, Linking, Animated } from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import { API_URL, defaultIntegrations } from './constants';

export const useIntegrations = (user: any) => {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [integrations, setIntegrations] = useState(defaultIntegrations);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [connectingKey, setConnectingKey] = useState<string | null>(null);
  
  const loadIntegrationsRef = useRef<{ 
    timeout: ReturnType<typeof setTimeout> | null; 
    isLoading: boolean; 
    lastLoadTime: number; 
    skipNextLoad: boolean 
  }>({ timeout: null, isLoading: false, lastLoadTime: 0, skipNextLoad: false });
  
  const currentAutoUploadServiceRef = useRef<string | null>(null);
  const lastFocusTimeRef = useRef(0);
  const pollingIntervalsRef = useRef<Record<string, ReturnType<typeof setInterval>>>({});
  const chainAnimations = useRef<Record<string, Animated.Value>>({}).current;

  useEffect(() => {
    // Cleanup all polling intervals on unmount
    return () => {
      Object.values(pollingIntervalsRef.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervalsRef.current = {};
    };
  }, []);

  // Initialize chain animations
  useEffect(() => {
    Object.keys(defaultIntegrations).forEach((key) => {
      if (!chainAnimations[key]) {
        chainAnimations[key] = new Animated.Value(0);
      }
    });
  }, []);

  const triggerChainAnimation = (key: string) => {
    setConnectingKey(key);
    Animated.timing(chainAnimations[key], {
      toValue: 1,
      duration: 800,
      useNativeDriver: true,
    }).start(() => {
      setConnectingKey(null);
    });
  };

  const loadIntegrations = useCallback(async () => {
    if (loadIntegrationsRef.current.skipNextLoad) {
      loadIntegrationsRef.current.skipNextLoad = false;
      return;
    }

    if (loadIntegrationsRef.current.isLoading) return;

    const now = Date.now();
    if (now - loadIntegrationsRef.current.lastLoadTime < 5000) return;

    if (loadIntegrationsRef.current.timeout) {
      clearTimeout(loadIntegrationsRef.current.timeout);
    }

    loadIntegrationsRef.current.isLoading = true;
    loadIntegrationsRef.current.timeout = setTimeout(async () => {
      try {
        const response = await axios.get(`${API_URL}/user-settings/${user.id}`);
        const permissions = response.data.permissions || {};

        let oauthStatus: Record<string, boolean> = {};
        try {
          const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
          oauthStatus = authResponse.data.status || {};
        } catch (err) {
          console.error('Error checking OAuth status:', err);
        }

        setIntegrations({
          appleNotes: permissions.notes || false,
          // All other data sources disabled - only Apple Notes supported
          appleCalendar: false,
          appleMusic: false,
          iosContacts: false,
          androidContacts: false,
          iosHealth: false,
          androidHealth: false,
          locationData: false,
          googleCalendar: false,
          gmail: false,
          googleDrive: false,
          mobileMessages: false,
          spotify: false,
          linkedin: false,
          outlook: false,
          github: false,
          notion: false,
          reddit: false,
          youtube: false,
          zoom: false,
          plaid: false,
        });
        loadIntegrationsRef.current.lastLoadTime = Date.now();
      } catch (error) {
        console.error('Error loading integrations:', error);
      } finally {
        loadIntegrationsRef.current.timeout = null;
        loadIntegrationsRef.current.isLoading = false;
      }
    }, 500);
  }, [user]);

  useEffect(() => {
    if (user) loadIntegrations();
  }, [user, loadIntegrations]);

  useFocusEffect(
    useCallback(() => {
      const autoUploadParam = params.autoUpload as string;
      let timer: ReturnType<typeof setTimeout> | null = null;

      if (autoUploadParam && user && currentAutoUploadServiceRef.current !== autoUploadParam) {
        currentAutoUploadServiceRef.current = autoUploadParam;
        router.replace('/(tabs)/two');

        timer = setTimeout(() => {
          handleAutoUpload(autoUploadParam);
          currentAutoUploadServiceRef.current = null;
        }, 1000);
      }

      return () => {
        if (timer) clearTimeout(timer);
      };
    }, [user, params.autoUpload])
  );

  const handleAutoUpload = async (service: string) => {
    const serviceToKey: Record<string, string> = {
      'calendar': 'googleCalendar',
      'gmail': 'gmail',
      'google_drive': 'googleDrive',
      'youtube': 'youtube'
    };

    const key = serviceToKey[service];
    if (!key) return;

    if (loading[key]) return;

    setLoading((prev) => ({ ...prev, [key]: true }));

    try {
      const response = await axios.get(`${API_URL}/user-settings/${user.id}`);
      const permissions = response.data.permissions || {};

      const keyToPermission: Record<string, string> = {
        'googleCalendar': 'calendar',
        'gmail': 'email',
        'googleDrive': 'googleDrive',
        'youtube': 'youtube'
      };

      const permissionField = keyToPermission[key];

      if (permissions[permissionField]) {
        setLoading((prev) => ({ ...prev, [key]: false }));
        return;
      }

      loadIntegrationsRef.current.lastLoadTime = Date.now();
      loadIntegrationsRef.current.skipNextLoad = true;

      const newPermissions = { ...integrations, [key]: true };

      const apiPermissions = {
        notes: newPermissions.appleNotes,
        appleCalendar: newPermissions.appleCalendar,
        appleMusic: newPermissions.appleMusic,
        iosContacts: newPermissions.iosContacts,
        androidContacts: newPermissions.androidContacts,
        iosHealth: newPermissions.iosHealth,
        androidHealth: newPermissions.androidHealth,
        locationData: newPermissions.locationData,
        calendar: newPermissions.googleCalendar,
        email: newPermissions.gmail,
        googleDrive: newPermissions.googleDrive,
        mobileMessages: newPermissions.mobileMessages,
        spotify: newPermissions.spotify,
        youtube: newPermissions.youtube,
      };

      await axios.post(`${API_URL}/save-permissions`, {
        user_id: user.id,
        permissions: apiPermissions,
      });

      triggerChainAnimation(key);
      
      if (key === 'youtube') {
        await axios.post(`${API_URL}/ingest-youtube`, { user_id: user.id });
      } else {
        await axios.post(`${API_URL}/upload-documents`, { user_id: user.id, permissions: apiPermissions });
      }

      setIntegrations(newPermissions);
      Alert.alert('SUCCESS', `${key} data uploaded successfully.`);
    } catch (error) {
      Alert.alert('PROTOCOL ERROR', `Failed to upload ${key} data.`);
    } finally {
      setLoading((prev) => ({ ...prev, [key]: false }));
    }
  };

  // Location data disabled - only Apple Notes supported
  // const handleLocationDataIngest = async () => {
  //   setLoading((prev) => ({ ...prev, locationData: true }));
  //   try {
  //     const { status } = await Location.requestForegroundPermissionsAsync();
  //     
  //     if (status !== 'granted') {
  //       Alert.alert('PERMISSION DENIED', 'Location permission is required to fetch your current location.');
  //       setLoading((prev) => ({ ...prev, locationData: false }));
  //       return;
  //     }

  //     const location = await Location.getCurrentPositionAsync({});
  //     
  //     const locationData = {
  //       current_location: {
  //         latitude: location.coords.latitude,
  //         longitude: location.coords.longitude,
  //         timestamp: new Date(location.timestamp).toISOString(),
  //         accuracy: location.coords.accuracy,
  //         altitude: location.coords.altitude,
  //         speed: location.coords.speed,
  //       }
  //     };

  //     await axios.post(`${API_URL}/ingest-current-location`, {
  //       user_id: user.id,
  //       platform: Platform.OS,
  //       location_data: locationData
  //     });

  //     Alert.alert('SUCCESS', 'Current location ingested successfully.');
  //   } catch (error) {
  //     console.error('Location error:', error);
  //     Alert.alert('ERROR', 'Failed to fetch or ingest location data.');
  //   } finally {
  //     setLoading((prev) => ({ ...prev, locationData: false }));
  //   }
  // };

  // Health data disabled - only Apple Notes supported
  // const handleHealthDataIngest = async (platform: 'ios' | 'android') => {
  //   const key = platform === 'ios' ? 'iosHealth' : 'androidHealth';
  //   setLoading((prev) => ({ ...prev, [key]: true }));
  //   try {
  //     Alert.alert(
  //       'HEALTH DATA',
  //       'Health data requires native modules to access HealthKit (iOS) or Google Fit (Android). This feature is not available in Expo Go. In production, you would fetch health data from the device and send it to the backend.',
  //       [
  //         { text: 'Cancel', style: 'cancel' },
  //         {
  //           text: 'Simulate',
  //           onPress: async () => {
  //             try {
  //               const startDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  //               const endDate = new Date();
  //               
  //               const healthData: {
  //                 data_type: string;
  //                 start_date: string;
  //                 end_date: string;
  //                 data: Array<{
  //                   data_type: string;
  //                   value: number | string;
  //                   unit: string;
  //                   date: string;
  //                 }>;
  //               } = {
  //                 data_type: 'all',
  //                 start_date: startDate.toISOString().split('T')[0],
  //                 end_date: endDate.toISOString().split('T')[0],
  //                 data: []
  //               };

  //               for (let i = 0; i < 7; i++) {
  //                 const date = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000);
  //                 const dateStr = date.toISOString();

  //                 healthData.data.push({
  //                   data_type: 'steps',
  //                   value: Math.floor(6000 + Math.random() * 8000),
  //                   unit: 'count',
  //                   date: dateStr
  //                 });

  //                 healthData.data.push({
  //                   data_type: 'heart_rate',
  //                   value: Math.floor(60 + Math.random() * 20),
  //                   unit: 'bpm',
  //                   date: dateStr
  //                 });

  //                 healthData.data.push({
  //                   data_type: 'distance',
  //                   value: (3 + Math.random() * 5).toFixed(2),
  //                   unit: 'km',
  //                   date: dateStr
  //                 });

  //                 healthData.data.push({
  //                   data_type: 'active_energy',
  //                   value: Math.floor(200 + Math.random() * 400),
  //                   unit: 'kcal',
  //                   date: dateStr
  //                 });

  //                 if (i % 2 === 0) {
  //                   healthData.data.push({
  //                     data_type: 'sleep',
  //                     value: (6 + Math.random() * 3).toFixed(1),
  //                     unit: 'hours',
  //                     date: dateStr
  //                   });
  //                 }
  //               }

  //               await axios.post(`${API_URL}/ingest-health-data`, {
  //                 user_id: user.id,
  //                 platform: platform,
  //                 health_data: healthData
  //               });

  //               Alert.alert('SUCCESS', `Health data ingested successfully (simulated ${healthData.data.length} data points).`);
  //             } catch (error) {
  //               console.error('Health data error:', error);
  //               Alert.alert('ERROR', 'Failed to ingest health data.');
  //             }
  //           }
  //         }
  //       ]
  //     );
  //   } catch (error) {
  //     console.error('Health data error:', error);
  //     Alert.alert('ERROR', 'Failed to process health data request.');
  //   } finally {
  //     setLoading((prev) => ({ ...prev, [key]: false }));
  //   }
  // };

  // Apple Music disabled - only Apple Notes supported
  // const handleAppleMusicConnect = async () => {
  //   Alert.alert('NOT AVAILABLE', 'Apple Music integration requires native modules not available in Expo Go');
  // };

  // Spotify disabled - only Apple Notes supported
  // const handleSpotifyConnect = async () => {
  //   setLoading((prev) => ({ ...prev, spotify: true }));
  //   try {
  //     console.log('[SPOTIFY] Requesting authorization URL');
  //     const response = await axios.get(`${API_URL}/spotify/authorize`, {
  //       params: { user_id: user.id }
  //     });

  //     console.log('[SPOTIFY] Authorization response:', response.data);
  //     const { authorization_url } = response.data;

  //     if (!authorization_url) {
  //       throw new Error('No authorization URL in response');
  //     }

  //     const supported = await Linking.canOpenURL(authorization_url);
  //     if (supported) {
  //       console.log('[SPOTIFY] Opening authorization URL');
  //       // Set OAuth in progress flag to prevent auto-logout
  //       await SecureStore.setItemAsync('oauth_in_progress', 'true');
  //       await Linking.openURL(authorization_url);

  //       // Clear any existing spotify polling interval
  //       if (pollingIntervalsRef.current['spotify']) {
  //         clearInterval(pollingIntervalsRef.current['spotify']);
  //         delete pollingIntervalsRef.current['spotify'];
  //       }

  //       let pollAttempts = 0;
  //       const maxAttempts = 150; // Increased from 90 to 150 (5 minutes)

  //       console.log('[SPOTIFY] Starting polling interval');
  //       const pollInterval = setInterval(async () => {
  //         pollAttempts++;

  //         try {
  //           const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
  //           const status = authResponse.data.status || {};
  //           console.log('[SPOTIFY POLL] Auth status:', status, 'Attempt:', pollAttempts);

  //           if (status.spotify || pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['spotify'];
  //             // Clear OAuth in progress flag
  //             await SecureStore.setItemAsync('oauth_in_progress', 'false');

  //             if (status.spotify) {
  //               console.log('[SPOTIFY] Authorization detected, starting data upload');
  //               const newPermissions = { ...integrations, spotify: true };

  //               const apiPermissions = {
  //                 notes: newPermissions.appleNotes,
  //                 appleCalendar: newPermissions.appleCalendar,
  //                 appleMusic: newPermissions.appleMusic,
  //                 iosContacts: newPermissions.iosContacts,
  //                 androidContacts: newPermissions.androidContacts,
  //                 iosHealth: newPermissions.iosHealth,
  //                 androidHealth: newPermissions.androidHealth,
  //                 locationData: newPermissions.locationData,
  //                 calendar: newPermissions.googleCalendar,
  //                 email: newPermissions.gmail,
  //                 googleDrive: newPermissions.googleDrive,
  //                 mobileMessages: newPermissions.mobileMessages,
  //                 spotify: newPermissions.spotify,
  //                 youtube: newPermissions.youtube,
  //               };

  //               await axios.post(`${API_URL}/save-permissions`, {
  //                 user_id: user.id,
  //                 permissions: apiPermissions,
  //               });

  //               triggerChainAnimation('spotify');
  //               await axios.post(`${API_URL}/ingest-spotify`, { user_id: user.id });

  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');

  //               setIntegrations(newPermissions);
  //               setLoading((prev) => ({ ...prev, spotify: false }));
  //               Alert.alert('SUCCESS', 'Spotify authorized and data uploaded successfully.');
  //             } else {
  //               console.log('[SPOTIFY] Polling timed out');
  //               // Clear OAuth in progress flag on timeout
  //               await SecureStore.deleteItemAsync('oauth_in_progress');
  //               setLoading((prev) => ({ ...prev, spotify: false }));
  //               Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
  //             }
  //           }
  //         } catch (err) {
  //           console.error('Error polling auth status:', err);
  //           // Clear OAuth in progress flag on error
  //           await SecureStore.deleteItemAsync('oauth_in_progress');
  //           if (pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['spotify'];
  //             setLoading((prev) => ({ ...prev, spotify: false }));
  //           }
  //         }
  //       }, 2000);

  //       pollingIntervalsRef.current['spotify'] = pollInterval;
  //     } else {
  //       Alert.alert('ERROR', 'Cannot open the authorization URL');
  //       setLoading((prev) => ({ ...prev, spotify: false }));
  //     }

  //   } catch (error: any) {
  //     console.error('[SPOTIFY] Error:', error);
  //     // Clear OAuth in progress flag on error
  //     await SecureStore.deleteItemAsync('oauth_in_progress');
  //     Alert.alert('PROTOCOL ERROR', `Failed to connect Spotify: ${error?.message || 'Please try again.'}`);
  //     setLoading((prev) => ({ ...prev, spotify: false }));
  //   }
  // };

  // GitHub disabled - only Apple Notes supported
  // const handleGitHubConnect = async () => {
  //   setLoading((prev) => ({ ...prev, github: true }));
  //   try {
  //     console.log('[GITHUB] Requesting authorization URL');
  //     const response = await axios.get(`${API_URL}/github/authorize`, {
  //       params: { user_id: user.id }
  //     });

  //     console.log('[GITHUB] Authorization response:', response.data);
  //     const { authorization_url } = response.data;

  //     if (!authorization_url) {
  //       throw new Error('No authorization URL in response');
  //     }

  //     const supported = await Linking.canOpenURL(authorization_url);
  //     if (supported) {
  //       console.log('[GITHUB] Opening authorization URL');
  //       // Set OAuth in progress flag to prevent auto-logout
  //       await SecureStore.setItemAsync('oauth_in_progress', 'true');
  //       await Linking.openURL(authorization_url);

  //       // Clear any existing github polling interval
  //       if (pollingIntervalsRef.current['github']) {
  //         clearInterval(pollingIntervalsRef.current['github']);
  //         delete pollingIntervalsRef.current['github'];
  //       }

  //       let pollAttempts = 0;
  //       const maxAttempts = 150; // 5 minutes

  //       console.log('[GITHUB] Starting polling interval');
  //       const pollInterval = setInterval(async () => {
  //         pollAttempts++;

  //         try {
  //           const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
  //           const status = authResponse.data.status || {};
  //           console.log('[GITHUB POLL] Auth status:', status, 'Attempt:', pollAttempts);

  //           if (status.github || pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['github'];
  //             // Clear OAuth in progress flag
  //             await SecureStore.setItemAsync('oauth_in_progress', 'false');

  //             if (status.github) {
  //               console.log('[GITHUB] Authorization detected, starting data upload');
  //               const newPermissions = { ...integrations, github: true };

  //               const apiPermissions = {
  //                 notes: newPermissions.appleNotes,
  //                 appleCalendar: newPermissions.appleCalendar,
  //                 appleMusic: newPermissions.appleMusic,
  //                 iosContacts: newPermissions.iosContacts,
  //                 androidContacts: newPermissions.androidContacts,
  //                 iosHealth: newPermissions.iosHealth,
  //                 androidHealth: newPermissions.androidHealth,
  //                 locationData: newPermissions.locationData,
  //                 calendar: newPermissions.googleCalendar,
  //                 email: newPermissions.gmail,
  //                 googleDrive: newPermissions.googleDrive,
  //                 mobileMessages: newPermissions.mobileMessages,
  //                 spotify: newPermissions.spotify,
  //                 youtube: newPermissions.youtube,
  //                 github: newPermissions.github,
  //               };

  //               await axios.post(`${API_URL}/save-permissions`, {
  //                 user_id: user.id,
  //                 permissions: apiPermissions,
  //               });

  //               triggerChainAnimation('github');
  //               await axios.post(`${API_URL}/ingest-github`, { user_id: user.id });

  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');

  //               setIntegrations(newPermissions);
  //               setLoading((prev) => ({ ...prev, github: false }));
  //               Alert.alert('SUCCESS', 'GitHub authorized and data uploaded successfully.');
  //             } else {
  //               console.log('[GITHUB] Polling timed out');
  //               // Clear OAuth in progress flag on timeout
  //               await SecureStore.deleteItemAsync('oauth_in_progress');
  //               setLoading((prev) => ({ ...prev, github: false }));
  //               Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
  //             }
  //           }
  //         } catch (err) {
  //           console.error('Error polling auth status:', err);
  //           // Clear OAuth in progress flag on error
  //           await SecureStore.deleteItemAsync('oauth_in_progress');
  //           if (pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['github'];
  //             setLoading((prev) => ({ ...prev, github: false }));
  //           }
  //         }
  //       }, 2000);

  //       pollingIntervalsRef.current['github'] = pollInterval;
  //     } else {
  //       Alert.alert('ERROR', 'Cannot open the authorization URL');
  //       setLoading((prev) => ({ ...prev, github: false }));
  //     }

  //   } catch (error: any) {
  //     console.error('[GITHUB] Error:', error);
  //     // Clear OAuth in progress flag on error
  //     await SecureStore.deleteItemAsync('oauth_in_progress');
  //     Alert.alert('PROTOCOL ERROR', `Failed to connect GitHub: ${error?.message || 'Please try again.'}`);
  //     setLoading((prev) => ({ ...prev, github: false }));
  //   }
  // };

  // YouTube disabled - only Apple Notes supported
  // const handleYouTubeConnect = async () => {
  //   setLoading((prev) => ({ ...prev, youtube: true }));
  //   try {
  //     console.log('[YOUTUBE] Requesting authorization URL');
  //     const response = await axios.get(`${API_URL}/auth/youtube`, {
  //       params: { user_id: user.id }
  //     });

  //     console.log('[YOUTUBE] Authorization response:', response.data);
  //     const { authorization_url } = response.data;

  //     if (!authorization_url) {
  //       throw new Error('No authorization URL in response');
  //     }

  //     // Set OAuth in progress flag to prevent auto-logout
  //     await SecureStore.setItemAsync('oauth_in_progress', 'true');

  //     const supported = await Linking.canOpenURL(authorization_url);
  //     if (supported) {
  //       console.log('[YOUTUBE] Opening authorization URL');
  //       await Linking.openURL(authorization_url);
        
  //       // Clear any existing youtube polling interval
  //       if (pollingIntervalsRef.current['youtube']) {
  //         clearInterval(pollingIntervalsRef.current['youtube']);
  //         delete pollingIntervalsRef.current['youtube'];
  //       }
        
  //       let pollAttempts = 0;
  //       const maxAttempts = 150;

  //       console.log('[YOUTUBE] Starting polling interval');
  //       const pollInterval = setInterval(async () => {
  //         pollAttempts++;

  //         try {
  //           const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
  //           const status = authResponse.data.status || {};
  //           console.log('[YOUTUBE POLL] Auth status:', status, 'Attempt:', pollAttempts);

  //           if (status.youtube || pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['youtube'];

  //             if (status.youtube) {
  //               console.log('[YOUTUBE] Authorization detected, starting data upload');
  //               const newPermissions = { ...integrations, youtube: true };

  //               const apiPermissions = {
  //                 notes: newPermissions.appleNotes,
  //                 appleCalendar: newPermissions.appleCalendar,
  //                 appleMusic: newPermissions.appleMusic,
  //                 iosContacts: newPermissions.iosContacts,
  //                 androidContacts: newPermissions.androidContacts,
  //                 iosHealth: newPermissions.iosHealth,
  //                 androidHealth: newPermissions.androidHealth,
  //                 locationData: newPermissions.locationData,
  //                 calendar: newPermissions.googleCalendar,
  //                 email: newPermissions.gmail,
  //                 googleDrive: newPermissions.googleDrive,
  //                 mobileMessages: newPermissions.mobileMessages,
  //                 spotify: newPermissions.spotify,
  //                 youtube: newPermissions.youtube,
  //               };

  //               await axios.post(`${API_URL}/save-permissions`, {
  //                 user_id: user.id,
  //                 permissions: apiPermissions,
  //               });

  //               triggerChainAnimation('youtube');
  //               await axios.post(`${API_URL}/ingest-youtube`, { user_id: user.id });

  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');

  //               setIntegrations(newPermissions);
  //               setLoading((prev) => ({ ...prev, youtube: false }));
  //               Alert.alert('SUCCESS', 'YouTube authorized and data uploaded successfully.');
  //             } else {
  //               console.log('[YOUTUBE] Polling timed out');
  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');
  //               setLoading((prev) => ({ ...prev, youtube: false }));
  //               Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
  //             }
  //           }
  //         } catch (err) {
  //           console.error('Error polling auth status:', err);
  //           // Clear OAuth in progress flag on error
  //           await SecureStore.deleteItemAsync('oauth_in_progress');
  //           if (pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['youtube'];
  //             setLoading((prev) => ({ ...prev, youtube: false }));
  //           }
  //         }
  //       }, 2000);
        
  //       pollingIntervalsRef.current['youtube'] = pollInterval;
  //     } else {
  //       Alert.alert('ERROR', 'Cannot open the authorization URL');
  //       setLoading((prev) => ({ ...prev, youtube: false }));
  //     }

  //   } catch (error: any) {
  //     console.error('[YOUTUBE] Error:', error);
  //     // Clear OAuth in progress flag on error
  //     await SecureStore.deleteItemAsync('oauth_in_progress');
  //     Alert.alert('PROTOCOL ERROR', `Failed to connect YouTube: ${error?.message || 'Please try again.'}`);
  //     setLoading((prev) => ({ ...prev, youtube: false }));
  //   }
  // };

  // Zoom disabled - only Apple Notes supported
  // const handleZoomConnect = async () => {
  //   setLoading((prev) => ({ ...prev, zoom: true }));
  //   try {
  //     console.log('[ZOOM] Requesting authorization URL');
  //     const response = await axios.get(`${API_URL}/zoom/authorize`, {
  //       params: { user_id: user.id }
  //     });

  //     console.log('[ZOOM] Authorization response:', response.data);
  //     const { authorization_url } = response.data;

  //     if (!authorization_url) {
  //       throw new Error('No authorization URL in response');
  //     }

  //     const supported = await Linking.canOpenURL(authorization_url);
  //     if (supported) {
  //       console.log('[ZOOM] Opening authorization URL');
  //       // Set OAuth in progress flag to prevent auto-logout
  //       await SecureStore.setItemAsync('oauth_in_progress', 'true');
  //       await Linking.openURL(authorization_url);

  //       // Clear any existing zoom polling interval
  //       if (pollingIntervalsRef.current['zoom']) {
  //         clearInterval(pollingIntervalsRef.current['zoom']);
  //         delete pollingIntervalsRef.current['zoom'];
  //       }

  //       let pollAttempts = 0;
  //       const maxAttempts = 150; // 5 minutes

  //       console.log('[ZOOM] Starting polling interval');
  //       const pollInterval = setInterval(async () => {
  //         pollAttempts++;

  //         try {
  //           const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
  //           const status = authResponse.data.status || {};
  //           console.log('[ZOOM POLL] Auth status:', status, 'Attempt:', pollAttempts);

  //           if (status.zoom || pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['zoom'];
  //             // Clear OAuth in progress flag
  //             await SecureStore.setItemAsync('oauth_in_progress', 'false');

  //             if (status.zoom) {
  //               console.log('[ZOOM] Authorization detected, starting data upload');
  //               const newPermissions = { ...integrations, zoom: true };

  //               const apiPermissions = {
  //                 notes: newPermissions.appleNotes,
  //                 appleCalendar: newPermissions.appleCalendar,
  //                 appleMusic: newPermissions.appleMusic,
  //                 iosContacts: newPermissions.iosContacts,
  //                 androidContacts: newPermissions.androidContacts,
  //                 iosHealth: newPermissions.iosHealth,
  //                 androidHealth: newPermissions.androidHealth,
  //                 locationData: newPermissions.locationData,
  //                 calendar: newPermissions.googleCalendar,
  //                 email: newPermissions.gmail,
  //                 googleDrive: newPermissions.googleDrive,
  //                 mobileMessages: newPermissions.mobileMessages,
  //                 spotify: newPermissions.spotify,
  //                 youtube: newPermissions.youtube,
  //                 zoom: newPermissions.zoom,
  //               };

  //               await axios.post(`${API_URL}/save-permissions`, {
  //                 user_id: user.id,
  //                 permissions: apiPermissions,
  //               });

  //               triggerChainAnimation('zoom');
  //               await axios.post(`${API_URL}/ingest-zoom`, { user_id: user.id });

  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');

  //               setIntegrations(newPermissions);
  //               setLoading((prev) => ({ ...prev, zoom: false }));
  //               Alert.alert('SUCCESS', 'Zoom authorized and data uploaded successfully.');
  //             } else {
  //               console.log('[ZOOM] Polling timed out');
  //               // Clear OAuth in progress flag on timeout
  //               await SecureStore.deleteItemAsync('oauth_in_progress');
  //               setLoading((prev) => ({ ...prev, zoom: false }));
  //               Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
  //             }
  //           }
  //         } catch (err) {
  //           console.error('Error polling auth status:', err);
  //           // Clear OAuth in progress flag on error
  //           await SecureStore.deleteItemAsync('oauth_in_progress');
  //           if (pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['zoom'];
  //             setLoading((prev) => ({ ...prev, zoom: false }));
  //           }
  //         }
  //       }, 2000);

  //       pollingIntervalsRef.current['zoom'] = pollInterval;
  //     } else {
  //       Alert.alert('ERROR', 'Cannot open the authorization URL');
  //       setLoading((prev) => ({ ...prev, zoom: false }));
  //     }

  //   } catch (error: any) {
  //     console.error('[ZOOM] Error:', error);
  //     // Clear OAuth in progress flag on error
  //     await SecureStore.deleteItemAsync('oauth_in_progress');
  //     Alert.alert('PROTOCOL ERROR', `Failed to connect Zoom: ${error?.message || 'Please try again.'}`);
  //     setLoading((prev) => ({ ...prev, zoom: false }));
  //   }
  // };

  // Notion disabled - only Apple Notes supported
  // const handleNotionConnect = async () => {
  //   setLoading((prev) => ({ ...prev, notion: true }));
  //   try {
  //     console.log('[NOTION] Requesting authorization URL');
  //     const response = await axios.get(`${API_URL}/notion/authorize`, {
  //       params: { user_id: user.id }
  //     });

  //     console.log('[NOTION] Authorization response:', response.data);
  //     const { authorization_url } = response.data;

  //     if (!authorization_url) {
  //       throw new Error('No authorization URL in response');
  //     }

  //     const supported = await Linking.canOpenURL(authorization_url);
  //     if (supported) {
  //       console.log('[NOTION] Opening authorization URL');
  //       // Set OAuth in progress flag to prevent auto-logout
  //       await SecureStore.setItemAsync('oauth_in_progress', 'true');
  //       await Linking.openURL(authorization_url);

  //       // Clear any existing notion polling interval
  //       if (pollingIntervalsRef.current['notion']) {
  //         clearInterval(pollingIntervalsRef.current['notion']);
  //         delete pollingIntervalsRef.current['notion'];
  //       }

  //       let pollAttempts = 0;
  //       const maxAttempts = 150; // 5 minutes

  //       console.log('[NOTION] Starting polling interval');
  //       const pollInterval = setInterval(async () => {
  //         pollAttempts++;

  //         try {
  //           const authResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
  //           const status = authResponse.data.status || {};
  //           console.log('[NOTION POLL] Auth status:', status, 'Attempt:', pollAttempts);

  //           if (status.notion || pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['notion'];
  //             // Clear OAuth in progress flag
  //             await SecureStore.setItemAsync('oauth_in_progress', 'false');

  //             if (status.notion) {
  //               console.log('[NOTION] Authorization detected, starting data upload');
  //               const newPermissions = { ...integrations, notion: true };

  //               const apiPermissions = {
  //                 notes: newPermissions.appleNotes,
  //                 appleCalendar: newPermissions.appleCalendar,
  //                 appleMusic: newPermissions.appleMusic,
  //                 iosContacts: newPermissions.iosContacts,
  //                 androidContacts: newPermissions.androidContacts,
  //                 iosHealth: newPermissions.iosHealth,
  //                 androidHealth: newPermissions.androidHealth,
  //                 locationData: newPermissions.locationData,
  //                 calendar: newPermissions.googleCalendar,
  //                 email: newPermissions.gmail,
  //                 googleDrive: newPermissions.googleDrive,
  //                 mobileMessages: newPermissions.mobileMessages,
  //                 spotify: newPermissions.spotify,
  //                 youtube: newPermissions.youtube,
  //                 notion: newPermissions.notion,
  //               };

  //               await axios.post(`${API_URL}/save-permissions`, {
  //                 user_id: user.id,
  //                 permissions: apiPermissions,
  //               });

  //               triggerChainAnimation('notion');
  //               await axios.post(`${API_URL}/ingest-notion`, { user_id: user.id });

  //               // Clear OAuth in progress flag
  //               await SecureStore.deleteItemAsync('oauth_in_progress');

  //               setIntegrations(newPermissions);
  //               setLoading((prev) => ({ ...prev, notion: false }));
  //               Alert.alert('SUCCESS', 'Notion authorized and data uploaded successfully.');
  //             } else {
  //               console.log('[NOTION] Polling timed out');
  //               // Clear OAuth in progress flag on timeout
  //               await SecureStore.deleteItemAsync('oauth_in_progress');
  //               setLoading((prev) => ({ ...prev, notion: false }));
  //               Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
  //             }
  //           }
  //         } catch (err) {
  //           console.error('Error polling auth status:', err);
  //           // Clear OAuth in progress flag on error
  //           await SecureStore.deleteItemAsync('oauth_in_progress');
  //           if (pollAttempts >= maxAttempts) {
  //             clearInterval(pollInterval);
  //             delete pollingIntervalsRef.current['notion'];
  //             setLoading((prev) => ({ ...prev, notion: false }));
  //           }
  //         }
  //       }, 2000);

  //       pollingIntervalsRef.current['notion'] = pollInterval;
  //     } else {
  //       Alert.alert('ERROR', 'Cannot open the authorization URL');
  //       setLoading((prev) => ({ ...prev, notion: false }));
  //     }

  //   } catch (error: any) {
  //     console.error('[NOTION] Error:', error);
  //     // Clear OAuth in progress flag on error
  //     await SecureStore.deleteItemAsync('oauth_in_progress');
  //     Alert.alert('PROTOCOL ERROR', `Failed to connect Notion: ${error?.message || 'Please try again.'}`);
  //     setLoading((prev) => ({ ...prev, notion: false }));
  //   }
  // };

  // Apple Calendar disabled - only Apple Notes supported
  // const connectAppleCalendar = async (email: string, password: string) => {
  //   setLoading((prev) => ({ ...prev, appleCalendar: true }));
  //   try {
  //     const newPermissions = { ...integrations, appleCalendar: true };

  //     const apiPermissions = {
  //       notes: newPermissions.appleNotes,
  //       appleCalendar: newPermissions.appleCalendar,
  //       appleMusic: newPermissions.appleMusic,
  //       iosContacts: newPermissions.iosContacts,
  //       androidContacts: newPermissions.androidContacts,
  //       iosHealth: newPermissions.iosHealth,
  //       androidHealth: newPermissions.androidHealth,
  //       locationData: newPermissions.locationData,
  //       calendar: newPermissions.googleCalendar,
  //       email: newPermissions.gmail,
  //       googleDrive: newPermissions.googleDrive,
  //       mobileMessages: newPermissions.mobileMessages,
  //       spotify: newPermissions.spotify,
  //     };

  //     await axios.post(`${API_URL}/save-permissions`, {
  //       user_id: user.id,
  //       permissions: apiPermissions,
  //     });

  //     triggerChainAnimation('appleCalendar');

  //     await axios.post(`${API_URL}/ingest-apple-calendar`, {
  //       user_id: user.id,
  //       apple_calendar_email: email,
  //       apple_calendar_password: password,
  //     });

  //     setIntegrations(newPermissions);
  //     Alert.alert('SUCCESS', 'Apple Calendar connected successfully.');
  //   } catch (error) {
  //     Alert.alert('PROTOCOL ERROR', 'Failed to connect Apple Calendar. Please check your credentials.');
  //   } finally {
  //     setLoading((prev) => ({ ...prev, appleCalendar: false }));
  //   }
  // };

  const toggleIntegration = async (key: string) => {
    // All non-Apple Notes data sources disabled
    // if (key === 'appleMusic' && !integrations.appleMusic) {
    //   await handleAppleMusicConnect();
    //   return;
    // }

    // if (key === 'spotify' && !integrations.spotify) {
    //   await handleSpotifyConnect();
    //   return;
    // }

    // if (key === 'youtube' && !integrations.youtube) {
    //   await handleYouTubeConnect();
    //   return;
    // }

    // if (key === 'github' && !integrations.github) {
    //   await handleGitHubConnect();
    //   return;
    // }

    // if (key === 'zoom' && !integrations.zoom) {
    //   await handleZoomConnect();
    //   return;
    // }

    // if (key === 'notion' && !integrations.notion) {
    //   await handleNotionConnect();
    //   return;
    // }

    if (key === 'mobileMessages') {
      Alert.alert('NOT AVAILABLE', 'Mobile messages integration requires native modules not available in Expo Go');
      return;
    }

    if (['linkedin', 'outlook', 'reddit', 'plaid'].includes(key)) {
      Alert.alert('COMING SOON', `${key.toUpperCase()} integration is currently under development.`);
      return;
    }

    // Apple Calendar disabled - only Apple Notes supported
    // if (key === 'appleCalendar' && !integrations.appleCalendar) {
    //   Alert.alert(
    //     'APPLE CALENDAR CREDENTIALS',
    //     'Enter your Apple ID and App-Specific Password for iCloud Calendar access.\n\nGenerate an App-Specific Password at: appleid.apple.com',
    //     [
    //       { text: 'Cancel', style: 'cancel' },
    //       {
    //         text: 'Connect',
    //         onPress: () => {
    //           Alert.prompt(
    //             'Apple ID Email',
    //             'Enter your Apple ID email',
    //             [
    //               { text: 'Cancel', style: 'cancel' },
    //               {
    //                 text: 'Next',
    //                 onPress: async (email?: string) => {
    //                   if (!email) return;
    //                   Alert.prompt(
    //                     'App-Specific Password',
    //                     'Enter your iCloud App-Specific Password',
    //                     [
    //                       { text: 'Cancel', style: 'cancel' },
    //                       {
    //                         text: 'Connect',
    //                         onPress: async (password?: string) => {
    //                           if (!password) return;
    //                           await connectAppleCalendar(email, password);
    //                         }
    //                       }
    //                     ],
    //                     'secure-text'
    //                   );
    //                 }
    //               }
    //             ]
    //           );
    //         }
    //       }
    //     ]
    //   );
    //   return;
    // }

    const isConnecting = !integrations[key as keyof typeof integrations];

    if (isConnecting) {
      Alert.alert(
        'WARNING: DATA INGESTION',
        'Once enabled, data ingestion cannot be disabled without deleting all of your data from the database. Are you sure you want to proceed?',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Proceed',
            style: 'destructive',
            onPress: async () => {
              setLoading((prev) => ({ ...prev, [key]: true }));
              try {
                const newPermissions = { ...integrations, [key]: true };

                const apiPermissions = {
                  notes: newPermissions.appleNotes,
                  // All other data sources disabled - only Apple Notes supported
                  appleCalendar: false,
                  appleMusic: false,
                  iosContacts: false,
                  androidContacts: false,
                  locationData: false,
                  calendar: false,
                  email: false,
                  googleDrive: false,
                  mobileMessages: false,
                  spotify: false,
                };

                await axios.post(`${API_URL}/save-permissions`, {
                  user_id: user.id,
                  permissions: apiPermissions,
                });

                triggerChainAnimation(key);

                if (key === 'appleNotes') await axios.post(`${API_URL}/ingest-apple-notes`, { user_id: user.id });
                // All other data sources disabled - only Apple Notes supported
                // else if (key === 'appleMusic') await axios.post(`${API_URL}/ingest-apple-music`, { user_id: user.id });
                // else if (key === 'iosContacts') await axios.post(`${API_URL}/ingest-ios-contacts`, { user_id: user.id, platform: 'ios' });
                // else if (key === 'androidContacts') await axios.post(`${API_URL}/ingest-android-contacts`, { user_id: user.id, platform: 'android' });
                // else if (key === 'iosHealth') await handleHealthDataIngest('ios');
                // else if (key === 'androidHealth') await handleHealthDataIngest('android');
                // else if (key === 'locationData') await handleLocationDataIngest();
                // else if (key === 'spotify') await axios.post(`${API_URL}/ingest-spotify`, { user_id: user.id });
                else if (['googleCalendar', 'gmail', 'googleDrive', 'youtube'].includes(key)) {
                  const serviceMap: Record<string, string> = {
                    googleCalendar: 'calendar',
                    gmail: 'gmail',
                    googleDrive: 'google_drive',
                    youtube: 'youtube'
                  };
                  const service = serviceMap[key];

                  try {
                    const authStatus = await axios.get(`${API_URL}/auth/status/${user.id}`);
                    const status = authStatus.data.status || {};

                    if (!status[service]) {
                      setLoading((prev) => ({ ...prev, [key]: false }));
                      
                      Alert.alert(
                        'AUTHORIZATION REQUIRED',
                        `You need to authorize ${key} before enabling data ingestion. You will be redirected to the authorization page.`,
                        [
                          {
                            text: 'Cancel',
                            style: 'cancel'
                          },
                          {
                            text: 'Authorize',
                            onPress: async () => {
                              const authResponse = await axios.get(`${API_URL}/auth/${service}`, {
                                params: { user_id: user.id }
                              });
                              
                              const { authorization_url } = authResponse.data;
                              
                              // Set OAuth in progress flag to prevent auto-logout
                              await SecureStore.setItemAsync('oauth_in_progress', 'true');
                              
                              const supported = await Linking.canOpenURL(authorization_url);
                              if (supported) {
                                await Linking.openURL(authorization_url);
                                
                                setLoading((prev) => ({ ...prev, [key]: true }));
                                
                                // Clear any existing polling interval for this service
                                if (pollingIntervalsRef.current[service]) {
                                  clearInterval(pollingIntervalsRef.current[service]);
                                  delete pollingIntervalsRef.current[service];
                                }
                                
                                let pollAttempts = 0;
                                const maxAttempts = 90;
                                
                                const pollInterval = setInterval(async () => {
                                  pollAttempts++;

                                  try {
                                    const statusResponse = await axios.get(`${API_URL}/auth/status/${user.id}`);
                                    const currentStatus = statusResponse.data.status || {};

                                    if (currentStatus[service] || pollAttempts >= maxAttempts) {
                                      clearInterval(pollInterval);
                                      delete pollingIntervalsRef.current[service];
                                      
                                      if (currentStatus[service]) {
                                        const apiPermissions = {
                                          notes: newPermissions.appleNotes,
                                          // All other data sources disabled - only Apple Notes supported
                                          appleCalendar: false,
                                          appleMusic: false,
                                          iosContacts: false,
                                          androidContacts: false,
                                          iosHealth: false,
                                          androidHealth: false,
                                          locationData: false,
                                          calendar: false,
                                          email: false,
                                          googleDrive: false,
                                          mobileMessages: false,
                                          spotify: false,
                                          youtube: false,
                                        };

                                        await axios.post(`${API_URL}/save-permissions`, {
                                          user_id: user.id,
                                          permissions: apiPermissions,
                                        });

                                        triggerChainAnimation(key);
                                        
                                        if (key === 'youtube') {
                                          await axios.post(`${API_URL}/ingest-youtube`, { user_id: user.id });
                                        } else {
                                          await axios.post(`${API_URL}/upload-documents`, { user_id: user.id, permissions: apiPermissions });
                                        }

                                        // Clear OAuth in progress flag
                                        await SecureStore.deleteItemAsync('oauth_in_progress');

                                        setIntegrations(newPermissions);
                                        setLoading((prev) => ({ ...prev, [key]: false }));
                                        Alert.alert('SUCCESS', `${key} authorized and data uploaded successfully.`);
                                      } else {
                                        // Clear OAuth in progress flag on timeout
                                        await SecureStore.deleteItemAsync('oauth_in_progress');
                                        setLoading((prev) => ({ ...prev, [key]: false }));
                                        Alert.alert('TIMEOUT', 'Authorization timed out. Please try again.');
                                      }
                                    }
                                  } catch (err) {
                                    console.error('Error polling auth status:', err);
                                    // Clear OAuth in progress flag on error
                                    await SecureStore.deleteItemAsync('oauth_in_progress');
                                    if (pollAttempts >= maxAttempts) {
                                      clearInterval(pollInterval);
                                      delete pollingIntervalsRef.current[service];
                                      setLoading((prev) => ({ ...prev, [key]: false }));
                                    }
                                  }
                                }, 2000);
                                
                                pollingIntervalsRef.current[service] = pollInterval;
                              } else {
                                Alert.alert('ERROR', 'Cannot open the authorization URL');
                                // Clear OAuth in progress flag on error
                                await SecureStore.deleteItemAsync('oauth_in_progress');
                              }
                            }
                          }
                        ]
                      );
                      return;
                    }
                  } catch (err) {
                    console.error('Error checking auth status:', err);
                  }

                  await axios.post(`${API_URL}/upload-documents`, { user_id: user.id, permissions: apiPermissions });
                }

                setIntegrations(newPermissions);
              } catch (error) {
                Alert.alert('PROTOCOL ERROR', `Failed to initialize ${key} connection.`);
              } finally {
                setLoading((prev) => ({ ...prev, [key]: false }));
              }
            }
          }
        ]
      );
      return;
    }

    Alert.alert(
      'WARNING: DATA DELETION',
      'To disable this data ingestion, you must delete your entire database and remove all data ingestion. This action cannot be undone. Are you sure you want to proceed?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Proceed',
          style: 'destructive',
          onPress: async () => {
            setLoading((prev) => ({ ...prev, [key]: true }));
            try {
              await axios.post(`${API_URL}/reset-user-database`, {
                user_id: user.id,
              });

              setIntegrations(defaultIntegrations);
              Alert.alert('SUCCESS', 'Database has been reset. All data ingestion protocols have been disabled.');
            } catch (error) {
              Alert.alert('PROTOCOL ERROR', 'Failed to reset database. Please try again.');
            } finally {
              setLoading((prev) => ({ ...prev, [key]: false }));
            }
          }
        }
      ]
    );
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  const handleClearData = async () => {
    Alert.alert(
      'WARNING: COMPLETE DATA DELETION',
      'This will delete your entire database including all chat history, OAuth tokens, and Pinecone index. This action cannot be undone. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete All Data',
          style: 'destructive',
          onPress: async () => {
            setLoading((prev) => ({ ...prev, clearData: true }));
            try {
              await axios.post(`${API_URL}/reset-user-database`, {
                user_id: user.id,
              });

              // Clear AsyncStorage cache for the user
              await AsyncStorage.removeItem(`insights_${user.id}`);
              await AsyncStorage.removeItem(`thoughts_${user.id}`);
              await AsyncStorage.removeItem(`categories_${user.id}`);

              setIntegrations(defaultIntegrations);
              Alert.alert('SUCCESS', 'All data has been deleted. Your database has been reset.');
            } catch (error) {
              Alert.alert('ERROR', 'Failed to delete data. Please try again.');
            } finally {
              setLoading((prev) => ({ ...prev, clearData: false }));
            }
          }
        }
      ]
    );
  };

  const handleDeleteAccount = async () => {
    Alert.alert(
      'WARNING: PERMANENT ACCOUNT DELETION',
      'This will permanently delete your account, all your data, and remove you from Supabase. This action cannot be undone. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Account',
          style: 'destructive',
          onPress: async () => {
            setLoading((prev) => ({ ...prev, deleteAccount: true }));
            try {
              // Call the new delete-account endpoint which handles Pinecone deletion and Supabase auth deletion
              await axios.post(`${API_URL}/auth/delete-account`, null, {
                params: { user_id: user.id }
              });

              // Clear AsyncStorage cache for the user
              await AsyncStorage.removeItem(`insights_${user.id}`);
              await AsyncStorage.removeItem(`thoughts_${user.id}`);
              await AsyncStorage.removeItem(`categories_${user.id}`);

              // Sign out from Supabase
              await supabase.auth.signOut();

              setIntegrations(defaultIntegrations);
              Alert.alert('SUCCESS', 'Your account has been permanently deleted.');
            } catch (error) {
              console.error('Delete account error:', error);
              // Even if deletion fails, sign out the user
              await supabase.auth.signOut();
              Alert.alert('ERROR', 'There was an error deleting your account. You have been signed out.');
            } finally {
              setLoading((prev) => ({ ...prev, deleteAccount: false }));
            }
          }
        }
      ]
    );
  };

  return {
    integrations,
    loading,
    connectingKey,
    chainAnimations,
    toggleIntegration,
    handleLogout,
    handleClearData,
    handleDeleteAccount,
  };
};
