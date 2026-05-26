import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  ScrollView,
  SafeAreaView,
  StyleSheet,
  StatusBar,
  Alert,
  Animated,
  Platform,
  TouchableOpacity,
  Text,
  ActivityIndicator,
} from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useCache } from '../../hooks/useCache';
import ChatHeader from '../../components/chat/ChatHeader';
import WelcomeScreen from '../../components/chat/WelcomeScreen';
import ChatMessage from '../../components/chat/ChatMessage';
import LoadingIndicator from '../../components/chat/LoadingIndicator';
import SourceModal from '../../components/chat/SourceModal';
import ChatInput from '../../components/chat/ChatInput';
import LoadingScreen from '../../components/LoadingScreen';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [routingDecision, setRoutingDecision] = useState<string | null>(null);
  const [routingReason, setRoutingReason] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [sessionId, setSessionId] = useState<string>(Date.now().toString());
  const [isKnowledgeSession, setIsKnowledgeSession] = useState<boolean>(false);
  const [initialPromptConsumed, setInitialPromptConsumed] = useState<boolean>(false);
  const scrollViewRef = useRef<ScrollView>(null);
  const healthCheckRef = useRef<{ timeout: ReturnType<typeof setTimeout> | null; checked: boolean }>({ timeout: null, checked: false });
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [sourceModalVisible, setSourceModalVisible] = useState(false);
  const [greetingVisible, setGreetingVisible] = useState(false);
  const [greetingText, setGreetingText] = useState('');
  const greetingSlideAnim = useRef(new Animated.Value(300)).current;

  const getSourceTitle = (source: any) => {
    if (!source || !source.metadata) return 'Source Document';

    const meta = source.metadata;

    // Priority order for title fields
    if (meta.headline) return meta.headline;
    if (meta.repo_name) return meta.repo_name;
    if (meta.company) return meta.company;
    if (meta.position) return meta.position;
    if (meta.folder) return meta.folder;
    if (meta.source_type) return meta.source_type.charAt(0).toUpperCase() + meta.source_type.slice(1);
    if (meta.filename) return meta.filename;
    if (meta.date) return `Document from ${meta.date}`;

    return 'Source Document';
  };
  
  // Animation for loading dots
  const dot1Anim = useRef(new Animated.Value(0)).current;
  const dot2Anim = useRef(new Animated.Value(0)).current;
  const dot3Anim = useRef(new Animated.Value(0)).current;
  
  useEffect(() => {
    if (loading) {
      const animateDots = () => {
        Animated.sequence([
          Animated.timing(dot1Anim, { toValue: 1, duration: 400, useNativeDriver: true }),
          Animated.timing(dot2Anim, { toValue: 1, duration: 400, useNativeDriver: true }),
          Animated.timing(dot3Anim, { toValue: 1, duration: 400, useNativeDriver: true }),
          Animated.timing(dot1Anim, { toValue: 0, duration: 400, useNativeDriver: true }),
          Animated.timing(dot2Anim, { toValue: 0, duration: 400, useNativeDriver: true }),
          Animated.timing(dot3Anim, { toValue: 0, duration: 400, useNativeDriver: true }),
        ]).start(animateDots);
      };
      animateDots();
    } else {
      dot1Anim.setValue(0);
      dot2Anim.setValue(0);
      dot3Anim.setValue(0);
    }
  }, [loading]);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setInitialLoading(false);
    });
    checkHealth();

    // Cleanup timeout on unmount
    return () => {
      if (healthCheckRef.current.timeout) {
        clearTimeout(healthCheckRef.current.timeout);
      }
    };
  }, []);

  useEffect(() => {
    // If session_id is passed in params, use it and clear the param
    if (params.sessionId && params.sessionId !== sessionId) {
      setSessionId(params.sessionId as string);
      // Clear loading state and query when switching sessions
      setLoading(false);
      setLoadingStage('');
      setQuery('');
      setRoutingDecision(null);
      setRoutingReason(null);
      setInitialPromptConsumed(false);
      setChatHistory([]); // Clear chat history before loading new session
      setGreetingVisible(false); // Hide greeting when loading a session
      // Clear the sessionId param after consuming it
      router.setParams({ sessionId: undefined } as any);
    }
    // Check if this is a knowledge session and clear the param
    if (params.isKnowledgeSession === 'true') {
      setIsKnowledgeSession(true);
      router.setParams({ isKnowledgeSession: undefined } as any);
    } else if (params.isKnowledgeSession === 'false') {
      setIsKnowledgeSession(false);
      router.setParams({ isKnowledgeSession: undefined } as any);
    }
  }, [params.sessionId, params.isKnowledgeSession, sessionId]);

  useEffect(() => {
    // If initialPrompt is passed in params (from knowledge tab), use it to start conversation
    // Only consume it once per navigation
    if (params.initialPrompt && !loading && chatHistory.length === 0 && !initialPromptConsumed) {
      const prompt = params.initialPrompt as string;
      setQuery(prompt);
      setInitialPromptConsumed(true);
      // Clear the initialPrompt param after consuming it
      router.setParams({ initialPrompt: undefined } as any);
      // Automatically send the message
      setTimeout(() => {
        handleQuery();
      }, 500);
    }
  }, [params.initialPrompt, loading, chatHistory, initialPromptConsumed]);

  useEffect(() => {
    if (user && sessionId) {
      loadChatHistory();
    }
  }, [user, sessionId]);

  useEffect(() => {
    // Show initial greeting when chat is empty and user is loaded
    const showInitialGreeting = async () => {
      if (user && chatHistory.length === 0 && !isKnowledgeSession) {
        try {
          const response = await axios.get(`${API_URL}/notes-count`, {
            params: { user_id: user.id }
          });
          const notesCount = response.data.count || 0;
          const greeting = `I've read ${notesCount} of your Apple Notes and am ready to discuss them.`;
          setGreetingText(greeting);
          setGreetingVisible(true);
          // Animate slide up
          Animated.timing(greetingSlideAnim, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }).start();
        } catch (error) {
          console.error('Error fetching notes count:', error);
          // Fallback greeting if count fetch fails
          const greeting = `I've read your Apple Notes and am ready to discuss them.`;
          setGreetingText(greeting);
          setGreetingVisible(true);
          Animated.timing(greetingSlideAnim, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }).start();
        }
      }
    };
    
    showInitialGreeting();
  }, [user, chatHistory.length, isKnowledgeSession]);

  const fetchHealth = async (): Promise<string> => {
    const response = await axios.get(`${API_URL}/health`);
    return response.data.status;
  };

  const { data: healthStatus, refetch: refetchHealth } = useCache<string>(
    'health_status',
    fetchHealth,
    {
      ttl: 60000, // 1 minute cache for health status
      staleWhileRevalidate: true,
    }
  );

  const checkHealth = async () => {
    // Prevent repeated health checks
    if (healthCheckRef.current.checked) {
      return;
    }

    // Clear any existing timeout
    if (healthCheckRef.current.timeout) {
      clearTimeout(healthCheckRef.current.timeout);
    }

    healthCheckRef.current.timeout = setTimeout(async () => {
      await refetchHealth();
      healthCheckRef.current.checked = true;
      healthCheckRef.current.timeout = null;
    }, 300); // 300ms debounce
  };

  const loadChatHistory = async () => {
    if (!user) return;
    // Don't load history for knowledge sessions - they should start fresh
    if (isKnowledgeSession) {
      setChatHistory([]);
      return;
    }
    try {
      setLoadingHistory(true);
      const response = await axios.post(`${API_URL}/chat-history/load`, {
        user_id: user.id,
        session_id: sessionId
      });
      console.log('Loaded chat history:', response.data);
      setChatHistory(response.data.messages || []);
    } catch (error) {
      console.error('Error loading chat history:', error);
      setChatHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const saveChatHistory = async (history: any[]) => {
    if (!user) return;
    // Don't save history for knowledge sessions - they should be ephemeral
    if (isKnowledgeSession) {
      return;
    }
    try {
      // Filter messages to only include fields expected by backend
      const filteredMessages = history
        .filter(msg => msg.role && msg.content) // Only save messages with required fields
        .map(msg => {
          const message: any = {
            role: msg.role,
            content: msg.content,
          };
          // Only include sources if they exist
          if (msg.sources && msg.sources.length > 0) {
            message.sources = msg.sources;
          }
          return message;
        });
      
      await axios.post(`${API_URL}/chat-history/save`, {
        user_id: user.id,
        session_id: sessionId,
        messages: filteredMessages,
      });
    } catch (error: any) {
      console.error('Error saving chat history:', error);
    }
  };

  const handleNewChat = () => {
    setSessionId(Date.now().toString());
    setChatHistory([]);
    setQuery('');
    setIsKnowledgeSession(false);
    setInitialPromptConsumed(false);
    setGreetingVisible(false);
    greetingSlideAnim.setValue(300);
    // Clear any lingering params
    router.setParams({ 
      initialPrompt: undefined, 
      sessionId: undefined, 
      isKnowledgeSession: undefined 
    } as any);
  };

  const handleQuery = async () => {
    if (!query.trim() || !user) return;

    // Hide greeting modal when user starts typing
    if (greetingVisible) {
      Animated.timing(greetingSlideAnim, {
        toValue: 300,
        duration: 300,
        useNativeDriver: true,
      }).start(() => setGreetingVisible(false));
    }

    const userMessage = { role: 'user', content: query };
    const newHistory = [...chatHistory, userMessage];
    setChatHistory(newHistory);
    setQuery('');
    setLoading(true);
    setRoutingDecision(null);
    setRoutingReason(null);
    setLoadingStage('Analyzing your query...');

    try {
      // Format conversation history for the API
      const conversationHistory = chatHistory
        .filter(msg => msg.role === 'user')
        .map((msg, idx) => ({
          query: msg.content,
          answer: chatHistory[idx * 2 + 1]?.content || ''
        }));

      setLoadingStage('Determining search strategy...');
      
      const response = await axios.post(`${API_URL}/query`, {
        question: query,
        user_id: user.id,
        session_id: sessionId,
        conversation_history: conversationHistory
      });
      
      // Store routing decision for display
      setRoutingDecision(response.data.routing_decision);
      setRoutingReason(response.data.routing_reason);
      
      // Update loading stage based on routing decision
      if (response.data.routing_decision === 'general') {
        setLoadingStage('Processing general conversation...');
        await new Promise(resolve => setTimeout(resolve, 300));
      } else {
        setLoadingStage('Searching your knowledge base...');
        await new Promise(resolve => setTimeout(resolve, 400));
        setLoadingStage('Ranking relevant documents...');
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      setLoadingStage('Generating response...');
      
      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources,
        routing_decision: response.data.routing_decision || 'knowledge',
        routing_reason: response.data.routing_reason || '',
      };
      const updatedHistory = [...newHistory, assistantMessage];
      setChatHistory(updatedHistory);
      saveChatHistory(updatedHistory);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'TERMINAL ERROR: Connection to the intelligence core lost.',
        sources: [],
      };
      const updatedHistory = [...newHistory, errorMessage];
      setChatHistory(updatedHistory);
      saveChatHistory(updatedHistory);
    } finally {
      setLoading(false);
      setLoadingStage('');
    }
  };

  if (initialLoading) {
    return <LoadingScreen message="Loading..." subtext="Preparing your chat" />;
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient
        colors={['#0f172a', '#020617', '#000000']}
        style={StyleSheet.absoluteFill}
      />
      
      <SafeAreaView style={styles.safeArea}>
        <ChatHeader
          onNewChat={handleNewChat}
          onClearHistory={() => setChatHistory([])}
        />

        <ScrollView
          ref={scrollViewRef}
          style={styles.chatArea}
          contentContainerStyle={styles.chatContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
          showsVerticalScrollIndicator={false}
        >
          {loadingHistory ? (
            <View style={{ padding: 20, alignItems: 'center' }}>
              <ActivityIndicator size="small" color="#9333ea" />
              <Text style={{ color: '#94a3b8', fontSize: 14, marginTop: 8 }}>Loading chat history...</Text>
            </View>
          ) : chatHistory.length === 0 ? (
            <WelcomeScreen iconSource={require('../../assets/images/adaptive-icon.png')} />
          ) : (
            chatHistory.map((message, index) => (
              <ChatMessage
                key={index}
                message={message}
                onSourcePress={(source) => {
                  setSelectedSource(source);
                  setSourceModalVisible(true);
                }}
                getSourceTitle={getSourceTitle}
              />
            ))
          )}

          {loading && (
            <LoadingIndicator
              loadingStage={loadingStage}
              routingDecision={routingDecision}
              dot1Anim={dot1Anim}
              dot2Anim={dot2Anim}
              dot3Anim={dot3Anim}
            />
          )}
        </ScrollView>

        <ChatInput
          query={query}
          setQuery={setQuery}
          loading={loading}
          onSend={handleQuery}
        />

        <SourceModal
          visible={sourceModalVisible}
          source={selectedSource}
          getSourceTitle={getSourceTitle}
          onClose={() => setSourceModalVisible(false)}
        />

        {/* Greeting Modal */}
        {greetingVisible && (
          <Animated.View style={[styles.greetingModal, { transform: [{ translateY: greetingSlideAnim }] }]}>
            <TouchableOpacity 
              style={styles.greetingCloseButton}
              onPress={() => {
                Animated.timing(greetingSlideAnim, {
                  toValue: 300,
                  duration: 300,
                  useNativeDriver: true,
                }).start(() => setGreetingVisible(false));
              }}
            >
              <Text style={styles.greetingCloseText}>✕</Text>
            </TouchableOpacity>
            <View style={styles.greetingBubble}>
              <View style={styles.greetingContent}>
                <Text style={styles.greetingText}>{greetingText}</Text>
              </View>
            </View>
          </Animated.View>
        )}
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
  chatArea: {
    flex: 1,
  },
  chatContent: {
    padding: 16,
    paddingBottom: 40,
  },
  greetingModal: {
    position: 'absolute',
    bottom: 150,
    left: 16,
    right: 16,
    paddingVertical: 24,
    paddingHorizontal: 20,
  },
  greetingCloseButton: {
    position: 'absolute',
    top: 12,
    right: 12,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },
  greetingCloseText: {
    color: '#9ca3af',
    fontSize: 16,
    fontWeight: '600',
  },
  greetingBubble: {
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
    shadowColor: '#8b5cf6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
  },
  greetingContent: {
    padding: 16,
  },
  greetingText: {
    color: '#e5e7eb',
    fontSize: 15,
    fontWeight: '500',
    lineHeight: 22,
  },
});
