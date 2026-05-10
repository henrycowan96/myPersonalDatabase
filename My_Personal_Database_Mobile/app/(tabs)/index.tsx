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

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';

export default function ChatScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState<string>('');
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
      const response = await axios.post(`${API_URL}/chat-history/load`, {
        user_id: user.id,
        session_id: sessionId
      });
      setChatHistory(response.data.messages || []);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const saveChatHistory = async (history: any[]) => {
    if (!user) return;
    // Don't save history for knowledge sessions - they should be ephemeral
    if (isKnowledgeSession) {
      return;
    }
    try {
      await axios.post(`${API_URL}/chat-history/save`, {
        user_id: user.id,
        session_id: sessionId,
        messages: history,
      });
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  };

  const handleNewChat = () => {
    setSessionId(Date.now().toString());
    setChatHistory([]);
    setQuery('');
    setIsKnowledgeSession(false);
    setInitialPromptConsumed(false);
    // Clear any lingering params
    router.setParams({ 
      initialPrompt: undefined, 
      sessionId: undefined, 
      isKnowledgeSession: undefined 
    } as any);
  };

  const handleQuery = async () => {
    if (!query.trim() || !user) return;

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
        routing_decision: response.data.routing_decision,
        routing_reason: response.data.routing_reason,
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
          {chatHistory.length === 0 ? (
            <WelcomeScreen iconSource={require('../../assets/images/icon.png')} />
          ) : (
            chatHistory.map((message, index) => (
              <View
                key={index}
                style={[
                  styles.messageRow,
                  { justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start' }
                ]}
              >
                <ChatMessage
                  message={message}
                  onSourcePress={(source) => {
                    setSelectedSource(source);
                    setSourceModalVisible(true);
                  }}
                  getSourceTitle={getSourceTitle}
                />
              </View>
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
    padding: 20,
    paddingBottom: 40,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
});
