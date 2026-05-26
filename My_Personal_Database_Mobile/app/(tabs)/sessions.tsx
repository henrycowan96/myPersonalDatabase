import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  StatusBar,
  Alert,
  Image,
} from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import { useRouter } from 'expo-router';
import {
  MessageSquare,
  Plus,
  Trash2,
  Clock,
  ChevronRight,
  Calendar,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import LoadingScreen from '../../components/LoadingScreen';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';

interface Session {
  session_id: string;
  created_at: string;
  message_count: number;
  last_message?: string;
}

export default function SessionsScreen() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
    });
  }, []);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    if (!user) return;
    
    try {
      setSessionsLoading(true);
      setSessionsError(null);
      
      // Use backend endpoint to fetch sessions with proper SQL aggregation
      const response = await axios.get(`${API_URL}/sessions/${user.id}`, {
        timeout: 10000, // 10 second timeout
      });
      
      console.log('Sessions response:', response.data);
      const sessionData = response.data.sessions || [];
      console.log('Session data:', sessionData);
      setSessions(sessionData);
    } catch (error) {
      console.error('Error fetching sessions:', error);
      
      // Handle specific error types
      let errorMessage = 'Failed to fetch sessions';
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 503) {
          errorMessage = error.response?.data?.detail || 'Backend service is currently unavailable. Please try again later.';
        } else if (error.code === 'ECONNABORTED') {
          errorMessage = 'Request timed out. Please check your connection and try again.';
        } else if (error.message.includes('Network Error')) {
          errorMessage = 'Network error. Please check your internet connection.';
        } else {
          errorMessage = error.response?.data?.detail || error.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      setSessionsError(errorMessage);
      setSessions([]); // Set empty array on error
    } finally {
      setSessionsLoading(false);
    }
  }, [user?.id, API_URL]);

  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [user]);

  const handleDeleteSession = async (sessionId: string) => {
    Alert.alert(
      'DELETE SESSION',
      'Are you sure you want to delete this session? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            setDeleting(sessionId);
            try {
              await supabase
                .from('chat_history')
                .delete()
                .eq('user_id', user.id)
                .eq('session_id', sessionId);

              await fetchSessions();
            } catch (error) {
              Alert.alert('ERROR', 'Failed to delete session');
            } finally {
              setDeleting(null);
            }
          }
        }
      ]
    );
  };

  const handleCreateNewSession = () => {
    // Navigate to chat tab, clearing any lingering params
    router.push({
      pathname: '/',
      params: {
        sessionId: undefined,
        initialPrompt: undefined,
        isKnowledgeSession: undefined
      }
    });
  };

  const handleSelectSession = (sessionId: string) => {
    // Navigate to chat tab with session_id, clearing any other params
    router.push({
      pathname: '/',
      params: { 
        sessionId,
        initialPrompt: undefined,
        isKnowledgeSession: undefined
      }
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

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
          <Text style={styles.title}>Sessions</Text>
          <TouchableOpacity onPress={handleCreateNewSession} style={styles.actionButton}>
            <Plus size={20} color="#fff" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.scrollArea} showsVerticalScrollIndicator={false}>
          {!user ? (
            <LoadingScreen message="Authenticating..." />
          ) : sessionsLoading ? (
            <LoadingScreen message="Loading sessions..." subtext="Retrieving your chat history" />
          ) : sessionsError ? (
            <View style={styles.errorState}>
              <View style={styles.errorIconContainer}>
                <Text style={styles.errorIcon}>⚠️</Text>
              </View>
              <Text style={styles.errorTitle}>ERROR LOADING SESSIONS</Text>
              <Text style={styles.errorSubtitle}>
                {sessionsError || 'Failed to load sessions. Please check your connection.'}
              </Text>
              <TouchableOpacity style={styles.retryButton} onPress={() => fetchSessions()}>
                <Text style={styles.retryButtonText}>RETRY</Text>
              </TouchableOpacity>
            </View>
          ) : sessions?.length === 0 ? (
            <View style={styles.emptyState}>
              <View style={styles.emptyIconContainer}>
                <MessageSquare size={48} color="#9333ea" />
              </View>
              <Text style={styles.emptyTitle}>NO SESSIONS</Text>
              <Text style={styles.emptySubtitle}>
                Start a new conversation in the Chat tab.
              </Text>
            </View>
          ) : (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>CHAT HISTORY</Text>
              <View style={styles.sectionCard}>
                {sessions?.map((session) => (
                  <TouchableOpacity
                    key={session.session_id}
                    onPress={() => handleSelectSession(session.session_id)}
                    activeOpacity={0.7}
                    style={styles.sessionItem}
                  >
                    <View style={styles.sessionItemContent}>
                      <View style={styles.sessionIconContainer}>
                        <LinearGradient
                          colors={['rgba(147, 51, 234, 0.2)', 'rgba(79, 70, 229, 0.1)']}
                          style={styles.sessionIconGradient}
                        >
                          <MessageSquare size={20} color="#9333ea" />
                        </LinearGradient>
                      </View>
                      <View style={styles.sessionTextContainer}>
                        <Text style={styles.sessionLabel}>SESSION {session.session_id ? session.session_id.slice(-6) : 'UNKNOWN'}</Text>
                        <View style={styles.sessionMeta}>
                          <Clock size={12} color="#64748b" />
                          <Text style={styles.sessionDate}>{formatDate(session.created_at)}</Text>
                          <Text style={styles.sessionDivider}>•</Text>
                          <Text style={styles.messageCount}>{session.message_count} messages</Text>
                        </View>
                      </View>
                      <TouchableOpacity
                        onPress={() => handleDeleteSession(session.session_id)}
                        disabled={deleting === session.session_id}
                        style={styles.deleteButton}
                        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                      >
                        {deleting === session.session_id ? (
                          <ActivityIndicator size="small" color="#ef4444" />
                        ) : (
                          <Trash2 size={18} color="#64748b" />
                        )}
                      </TouchableOpacity>
                      <ChevronRight size={18} color="#475569" style={{ marginLeft: 8 }} />
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}
        </ScrollView>
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
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 34,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: -0.5,
  },
  actionButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1e293b',
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollArea: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    color: '#cbd5e1',
    fontSize: 16,
    fontWeight: '500',
    marginTop: 16,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 40,
  },
  emptyIconContainer: {
    width: 100,
    height: 100,
    borderRadius: 32,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.2)',
  },
  emptyTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 4,
    marginBottom: 12,
    textTransform: 'uppercase',
  },
  emptySubtitle: {
    color: '#94a3b8',
    textAlign: 'center',
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '500',
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
  sessionItem: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  sessionItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  sessionIconContainer: {
    marginRight: 16,
  },
  sessionIconGradient: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionTextContainer: {
    flex: 1,
  },
  sessionLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  sessionMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sessionDate: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 4,
  },
  sessionDivider: {
    color: '#475569',
    fontSize: 12,
    marginHorizontal: 8,
  },
  messageCount: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '500',
  },
  deleteButton: {
    padding: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.05)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.1)',
  },
  errorState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 40,
  },
  errorIconContainer: {
    width: 100,
    height: 100,
    borderRadius: 32,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.2)',
  },
  errorIcon: {
    fontSize: 48,
  },
  errorTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 4,
    marginBottom: 12,
    textTransform: 'uppercase',
  },
  errorSubtitle: {
    color: '#94a3b8',
    textAlign: 'center',
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 24,
    fontWeight: '500',
  },
  retryButton: {
    backgroundColor: '#9333ea',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 1,
  },
});
