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
          <View style={styles.headerLeft}>
            <Image 
              source={require('../../assets/images/icon.png')} 
              style={styles.headerIcon}
            />
            <Text style={styles.title}>Settings</Text>
          </View>
          <TouchableOpacity style={styles.profileButton}>
            <LinearGradient
              colors={['#1e293b', '#0f172a']}
              style={styles.profileIcon}
            >
              <CircleUser size={20} color="#9333ea" />
            </LinearGradient>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollArea} showsVerticalScrollIndicator={false}>
          {/* Profile Row */}
          <View style={styles.profileRow}>
            <View style={styles.profileInfo}>
              <Text style={styles.profileEmail}>
                {user?.email || 'ANONYMOUS'}
              </Text>
              <Text style={styles.profileLabel}>
                USER
              </Text>
            </View>
          </View>

          {/* Integrations Section - Grid Layout */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>DATA INGESTION PROTOCOLS</Text>
            
            <View style={styles.gridContainer}>
              {integrationItems.map(({ key, label, icon: Icon, image, color }) => {
                const isConnected = integrations[key as keyof typeof integrations];
                
                const animatedScale = chainAnimations[key]?.interpolate({
                  inputRange: [0, 1],
                  outputRange: [1, 1.05],
                }) || 1;

                return (
                  <TouchableOpacity
                    key={key}
                    onPress={() => toggleIntegration(key)}
                    disabled={loading[key]}
                    activeOpacity={0.7}
                    style={styles.gridItem}
                  >
                    <Animated.View style={[
                      styles.gridCard,
                      {
                        borderColor: isConnected ? color : 'rgba(255,255,255,0.1)',
                        backgroundColor: isConnected ? `${color}20` : 'rgba(0,0,0,0.4)',
                        transform: [{ scale: animatedScale }],
                      }
                    ]}>
                      {loading[key] ? (
                        <ActivityIndicator size={24} color={color} />
                      ) : isConnected ? (
                        <Check size={24} color={color} />
                      ) : image ? (
                        key === 'plaid' && !isConnected ? (
                          <View style={styles.plaidIconContainer}>
                            <Image source={image} style={styles.gridImage} resizeMode="contain" />
                          </View>
                        ) : (
                          <Image 
                            source={image} 
                            style={
                              ['appleNotes', 'iosHealth', 'androidHealth'].includes(key) 
                                ? styles.gridImageExtraLarge
                                : key === 'linkedin'
                                ? styles.gridImageMediumLarge
                                : ['github', 'reddit', 'spotify'].includes(key)
                                ? styles.gridImageLarge 
                                : styles.gridImage
                            } 
                            resizeMode="contain" 
                          />
                        )
                      ) : Icon ? (
                        <Icon size={24} color={color} />
                      ) : null}
                    </Animated.View>
                    <Text style={[
                      styles.gridLabel,
                      { color: isConnected ? color : '#64748b' }
                    ]}>
                      {label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          {/* System Actions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>SYSTEM OPERATIONS</Text>

            <TouchableOpacity onPress={handleClearData} style={styles.clearDataButton}>
              {loading.clearData ? (
                <ActivityIndicator size="small" color="#ef4444" />
              ) : (
                <>
                  <Shield size={20} color="#ef4444" />
                  <Text style={styles.clearDataText}>CLEAR MY DATA</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
              <LogOut size={20} color="#ef4444" />
              <Text style={styles.logoutText}>LOG OUT</Text>
            </TouchableOpacity>

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
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 4,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerIcon: {
    width: 32,
    height: 32,
    marginRight: 12,
    borderRadius: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  profileButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(147, 51, 234, 0.3)',
  },
  scrollArea: {
    flex: 1,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.05)',
  },
  profileCard: {
    width: 60,
    height: 60,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(147, 51, 234, 0.3)',
    shadowColor: '#9333ea',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
  },
  profileInfo: {
    marginLeft: 16,
    flex: 1,
  },
  profileEmail: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  profileLabel: {
    color: '#9333ea',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
    marginTop: 4,
  },
  section: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  sectionTitle: {
    color: '#475569',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 3,
    marginBottom: 16,
    marginLeft: 8,
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -8,
  },
  gridItem: {
    width: '25%',
    paddingHorizontal: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  gridCard: {
    width: '100%',
    aspectRatio: 1,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  gridLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    marginTop: 8,
    textAlign: 'center',
  },
  gridImage: {
    width: 32,
    height: 32,
  },
  gridImageLarge: {
    width: 40,
    height: 40,
  },
  gridImageMediumLarge: {
    width: 36,
    height: 36,
  },
  gridImageExtraLarge: {
    width: 52,
    height: 52,
  },
  plaidIconContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  clearDataButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    height: 60,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
    marginBottom: 12,
  },
  clearDataText: {
    color: '#ef4444',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 2,
    marginLeft: 12,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    height: 60,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
  },
  logoutText: {
    color: '#ef4444',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 2,
    marginLeft: 12,
  },
  systemMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
    opacity: 0.4,
  },
  metaText: {
    color: '#64748b',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 2,
    marginLeft: 8,
  },
});
