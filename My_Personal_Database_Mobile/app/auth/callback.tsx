import { useEffect } from 'react';
import { View, ActivityIndicator, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';

export default function AuthCallback() {
  const router = useRouter();
  const params = useLocalSearchParams();

  useEffect(() => {
    const handleCallback = async () => {
      const { service, success, error } = params;

      console.log('[CALLBACK] Received params:', { service, success, error });

      const getErrorMessage = (err: string | string[] | undefined): string => {
        if (Array.isArray(err)) {
          return err[0] || 'An error occurred';
        }
        return err || 'An error occurred';
      };

      const getServiceValue = (svc: string | string[] | undefined): string => {
        if (Array.isArray(svc)) {
          return svc[0] || '';
        }
        return svc || '';
      };

      const serviceValue = getServiceValue(service);
      console.log('[CALLBACK] Service value:', serviceValue);

      if (serviceValue === 'spotify') {
        if (success === 'true') {
          Alert.alert('SUCCESS', 'Spotify integration completed successfully!');
        } else {
          Alert.alert('ERROR', getErrorMessage(error) || 'Spotify integration failed. Please try again.');
        }
      } else if (serviceValue === 'github') {
        if (success === 'true') {
          Alert.alert('SUCCESS', 'GitHub integration completed successfully!');
        } else {
          Alert.alert('ERROR', getErrorMessage(error) || 'GitHub integration failed. Please try again.');
        }
      } else if (serviceValue && ['calendar', 'gmail', 'google_drive', 'youtube'].includes(serviceValue)) {
        if (success === 'true') {
          Alert.alert('SUCCESS', `${serviceValue} authorized successfully! Your data will be uploaded automatically.`);
          console.log('[CALLBACK] Navigating to settings with autoUpload:', serviceValue);
          // Navigate to settings with service parameter to trigger auto-upload
          setTimeout(() => {
            router.replace(`/(tabs)/two?autoUpload=${serviceValue}`);
          }, 500);
          return;
        } else {
          Alert.alert('ERROR', getErrorMessage(error) || `${serviceValue} authorization failed. Please try again.`);
        }
      }

      // Navigate to settings after a short delay
      setTimeout(() => {
        router.replace('/(tabs)/two');
      }, 500);
    };

    handleCallback();
  }, [params, router]);

  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000' }}>
      <ActivityIndicator size="large" color="#9333ea" />
    </View>
  );
}
