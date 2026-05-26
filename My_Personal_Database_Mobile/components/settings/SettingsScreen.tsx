import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Animated,
  Dimensions,
  Image,
} from 'react-native';
import {
  Settings,
  CircleUser,
  Shield,
  LogOut,
  Cpu,
  Check,
  ChevronRight,
  Database,
  User,
  Bell,
  Lock,
  Globe,
  Info,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { integrationItems } from './constants';

const { width } = Dimensions.get('window');

interface SettingsScreenProps {
  user: any;
  integrations: any;
  loading: Record<string, boolean>;
  chainAnimations: Record<string, Animated.Value>;
  toggleIntegration: (key: string) => void;
  handleLogout: () => void;
  handleClearData: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({
  user,
  integrations,
  loading,
  chainAnimations,
  toggleIntegration,
  handleLogout,
  handleClearData,
}) => {
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient
        colors={['#0f172a', '#020617', '#000000']}
        style={StyleSheet.absoluteFill}
      />
      
      <SafeAreaView style={styles.safeArea}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
        </View>

        <ScrollView style={styles.scrollArea} showsVerticalScrollIndicator={false}>
          {/* Profile Card */}
          <View style={styles.profileCard}>
            <LinearGradient
              colors={['rgba(147, 51, 234, 0.2)', 'rgba(79, 70, 229, 0.1)']}
              style={styles.profileGradient}
            >
              <View style={styles.profileAvatar}>
                <LinearGradient
                  colors={['#9333ea', '#4f46e5']}
                  style={styles.avatarGradient}
                >
                  <User size={32} color="#fff" />
                </LinearGradient>
              </View>
              <View style={styles.profileDetails}>
                <Text style={styles.profileName}>
                  {user?.email?.split('@')[0] || 'User'}
                </Text>
                <Text style={styles.profileEmail}>
                  {user?.email || 'ANONYMOUS'}
                </Text>
              </View>
            </LinearGradient>
          </View>

          {/* Data Sources Section */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>DATA SOURCES</Text>
            <View style={styles.sectionCard}>
              {integrationItems.map(({ key, label, image, color }) => {
                const isConnected = integrations[key as keyof typeof integrations];
                const animatedScale = chainAnimations[key]?.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.02],
                }) || 1;
                const isAppleNotes = key === 'appleNotes';

                return (
                  <TouchableOpacity
                    key={key}
                    onPress={() => toggleIntegration(key)}
                    disabled={loading[key]}
                    activeOpacity={0.7}
                    style={styles.settingItem}
                  >
                    <Animated.View style={[styles.settingItemContent, { transform: [{ scale: animatedScale }] }]}>
                      <View style={styles.settingIconContainer}>
                        <LinearGradient
                          colors={isConnected ? [color, `${color}cc`] : ['rgba(255,255,255,0.05)', 'rgba(255,255,255,0.02)']}
                          style={styles.settingIconGradient}
                        >
                          {loading[key] ? (
                            <ActivityIndicator size={20} color={isConnected ? '#fff' : '#64748b'} />
                          ) : isConnected ? (
                            <Check size={20} color="#fff" />
                          ) : (
                            <Image 
                              source={image} 
                              style={styles.settingIcon}
                              resizeMode="contain" 
                            />
                          )}
                        </LinearGradient>
                      </View>
                      <View style={styles.settingTextContainer}>
                        <Text style={[styles.settingLabel, { color: isConnected ? '#fff' : '#94a3b8' }]}>
                          {label}
                        </Text>
                        <Text style={styles.settingDescription}>
                          {isConnected ? 'Connected' : 'Not connected'}
                        </Text>
                      </View>
                      <ChevronRight size={20} color="#475569" />
                    </Animated.View>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* System Section */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>SYSTEM</Text>
            <View style={styles.sectionCard}>
              <TouchableOpacity onPress={handleClearData} style={styles.settingItem}>
                <View style={styles.settingItemContent}>
                  <View style={styles.settingIconContainer}>
                    <LinearGradient
                      colors={['rgba(239, 68, 68, 0.2)', 'rgba(239, 68, 68, 0.1)']}
                      style={styles.settingIconGradient}
                    >
                      {loading.clearData ? (
                        <ActivityIndicator size={20} color="#ef4444" />
                      ) : (
                        <Database size={20} color="#ef4444" />
                      )}
                    </LinearGradient>
                  </View>
                  <View style={styles.settingTextContainer}>
                    <Text style={[styles.settingLabel, styles.dangerText]}>Clear Data</Text>
                    <Text style={styles.settingDescription}>Delete all your information</Text>
                  </View>
                  <ChevronRight size={20} color="#475569" />
                </View>
              </TouchableOpacity>

              <TouchableOpacity onPress={handleLogout} style={styles.settingItem}>
                <View style={styles.settingItemContent}>
                  <View style={styles.settingIconContainer}>
                    <LinearGradient
                      colors={['rgba(239, 68, 68, 0.2)', 'rgba(239, 68, 68, 0.1)']}
                      style={styles.settingIconGradient}
                    >
                      <LogOut size={20} color="#ef4444" />
                    </LinearGradient>
                  </View>
                  <View style={styles.settingTextContainer}>
                    <Text style={[styles.settingLabel, styles.dangerText]}>Log Out</Text>
                    <Text style={styles.settingDescription}>Sign out of your account</Text>
                  </View>
                  <ChevronRight size={20} color="#475569" />
                </View>
              </TouchableOpacity>
            </View>
          </View>

          {/* About Section */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>ABOUT</Text>
            <View style={styles.sectionCard}>
              <TouchableOpacity style={styles.settingItem}>
                <View style={styles.settingItemContent}>
                  <View style={styles.settingIconContainer}>
                    <LinearGradient
                      colors={['rgba(147, 51, 234, 0.2)', 'rgba(79, 70, 229, 0.1)']}
                      style={styles.settingIconGradient}
                    >
                      <Info size={20} color="#9333ea" />
                    </LinearGradient>
                  </View>
                  <View style={styles.settingTextContainer}>
                    <Text style={styles.settingLabel}>Version</Text>
                    <Text style={styles.settingDescription}>1.0.0</Text>
                  </View>
                </View>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerText}>Personal Database</Text>
            <Text style={styles.footerSubtext}>© 2026 All rights reserved</Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  safeArea: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 8,
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: -0.5,
  },
  scrollArea: {
    flex: 1,
  },
  profileCard: {
    marginHorizontal: 16,
    marginBottom: 24,
    borderRadius: 20,
    overflow: 'hidden',
    shadowColor: '#9333ea',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 8,
  },
  profileGradient: {
    padding: 20,
  },
  profileAvatar: {
    marginBottom: 16,
  },
  avatarGradient: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  profileDetails: {
    marginLeft: 0,
  },
  profileName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#fff',
    marginBottom: 4,
  },
  profileEmail: {
    fontSize: 14,
    fontWeight: '500',
    color: 'rgba(255, 255, 255, 0.6)',
  },
  section: {
    marginBottom: 32,
  },
  sectionHeader: {
    fontSize: 13,
    fontWeight: '600',
    color: '#64748b',
    letterSpacing: 1.5,
    marginBottom: 12,
    paddingHorizontal: 24,
    textTransform: 'uppercase',
  },
  sectionCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    marginHorizontal: 16,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  settingItem: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  settingItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  settingIconContainer: {
    marginRight: 16,
  },
  settingIconGradient: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingIcon: {
    width: 24,
    height: 24,
  },
  settingTextContainer: {
    flex: 1,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 2,
  },
  settingDescription: {
    fontSize: 13,
    fontWeight: '400',
    color: '#64748b',
  },
  dangerText: {
    color: '#ef4444',
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 24,
  },
  footerText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 4,
  },
  footerSubtext: {
    fontSize: 12,
    fontWeight: '400',
    color: '#64748b',
  },
});
