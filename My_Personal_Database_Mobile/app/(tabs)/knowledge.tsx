import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  Alert,
  StatusBar,
  Animated,
  Dimensions,
} from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';
import { Brain, AlertTriangle, Star, TrendingUp, Zap } from 'lucide-react-native';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';
import { useRouter } from 'expo-router';
import KnowledgeHeader from '../../components/knowledge/KnowledgeHeader';
import CategoryFilter from '../../components/knowledge/CategoryFilter';
import InsightCard from '../../components/knowledge/InsightCard';
import LLMThoughtCard from '../../components/knowledge/LLMThoughtCard';
import InsightDetailModal from '../../components/knowledge/InsightDetailModal';
import DocumentModal from '../../components/knowledge/DocumentModal';
import LLMThoughtModal from '../../components/knowledge/LLMThoughtModal';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';
const { width } = Dimensions.get('window');

// Make function globally available
declare global {
  var handleChatWithContext: (router: any, user: User | null, contentType: string, contentId: string, title: string, content: string, onClose?: () => void) => Promise<void>;
}

const handleChatWithContext = async (router: any, user: User | null, contentType: string, contentId: string, title: string, content: string, onClose?: () => void) => {
  console.log('handleChatWithContext called!', { router, user, contentType, contentId, title, API_URL });
  try {
    const response = await axios.post(`${API_URL}/chat-context`, {
      user_id: user?.id || '',
      content_type: contentType,
      content_id: contentId,
      title: title,
      content: content
    });

    if (response.data.success) {
      // Generate a unique temporary session ID for this specific chat
      const tempSessionId = `knowledge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Close the modal first if provided
      if (onClose) {
        onClose();
      }
      // Navigate to chat tab with the generated prompt, temporary session ID, and flag indicating this is a knowledge session
      router.push('/' as any);
      // Then set the prompt and session ID after navigation
      setTimeout(() => {
        router.setParams({ 
          initialPrompt: response.data.prompt,
          sessionId: tempSessionId,
          isKnowledgeSession: 'true'
        } as any);
      }, 100);
    } else {
      Alert.alert('Error', 'Failed to create chat context');
    }
  } catch (error) {
    console.error('Chat context error:', error);
    Alert.alert('Error', 'Failed to create chat context');
  }
};

const CACHE_KEYS = {
  insights: (userId: string) => `insights_${userId}`,
  thoughts: (userId: string) => `thoughts_${userId}`,
  categories: (userId: string) => `categories_${userId}`,
};

interface User {
  id?: string;
  user_id?: string;
  app_metadata: any;
  user_metadata: any;
}

interface Insight {
  id: string;
  category: string;
  title: string;
  description: string;
  significance_score: number;
  sources: any[];
  detected_at: string;
  time_context: Record<string, any>;
  entities: string[];
  actionable: boolean;
}

interface LLMThought {
  id: string;
  thought_type: string;
  title: string;
  content: string;
  prompt_used: string;
  generated_at: string;
}

interface DocumentInfo {
  id: string;
  title?: string;
  source: string;
  type: string;
  content?: string;
  snippet?: string;
  metadata: Record<string, any>;
  relevance_score?: number;
}

export default function KnowledgeScreen() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [insights, setInsights] = useState<Insight[]>([]);
  const [filteredInsights, setFilteredInsights] = useState<Insight[]>([]);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentInfo | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [detectedCategories, setDetectedCategories] = useState<string[]>([]);
  const [llmThoughts, setLLMThoughts] = useState<LLMThought[]>([]);
  const [loadingThoughts, setLoadingThoughts] = useState(false);
  const [selectedThought, setSelectedThought] = useState<LLMThought | null>(null);
  const colorScheme = useColorScheme();
  
  const panY = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      if (user) {
        loadAllData(user.id);
      }
    });
  }, []);

  const loadAllData = async (userId: string) => {
    // Try DB first (persistent across devices), then AsyncStorage (offline fallback)
    const hasData = await loadFromDB(userId);
    if (!hasData) {
      await loadFromCache(userId);
    }
    // NOTE: We intentionally do NOT auto-refresh from API here.
    // Insights are regenerated in the background after data upload.
    // Users can manually refresh via pull-to-refresh.
  };

  const loadFromDB = async (userId: string): Promise<boolean> => {
    try {
      const [insightsRes, thoughtsRes] = await Promise.all([
        axios.get(`${API_URL}/insights/load/${userId}?limit=20`).catch(() => null),
        axios.get(`${API_URL}/llm-thoughts/load/${userId}`).catch(() => null),
      ]);

      let hasInsights = false;
      let hasThoughts = false;

      if (insightsRes?.data?.insights?.length) {
        const dbInsights = insightsRes.data.insights;
        setInsights(dbInsights);
        setFilteredInsights(dbInsights.filter((i: Insight) => i.significance_score >= 0.7));

        // Extract categories
        const categories = ['all'];
        const uniqueGroups = new Set();
        dbInsights.forEach((insight: Insight) => {
          if (insight.time_context?.group) uniqueGroups.add(insight.time_context.group);
          if (insight.category && !categories.includes(insight.category)) categories.push(insight.category);
        });
        uniqueGroups.forEach((g: unknown) => {
          const s = String(g);
          if (!categories.includes(s)) categories.push(s);
        });
        setDetectedCategories(categories);
        hasInsights = true;
      }

      if (thoughtsRes?.data?.thoughts?.length) {
        setLLMThoughts(thoughtsRes.data.thoughts);
        hasThoughts = true;
      }

      return hasInsights || hasThoughts;
    } catch (e) {
      console.warn('Failed to load from DB', e);
      return false;
    }
  };

  const loadFromCache = async (userId: string): Promise<boolean> => {
    try {
      const cachedInsights = await AsyncStorage.getItem(CACHE_KEYS.insights(userId));
      const cachedThoughts = await AsyncStorage.getItem(CACHE_KEYS.thoughts(userId));
      const cachedCategories = await AsyncStorage.getItem(CACHE_KEYS.categories(userId));

      if (cachedInsights) {
        const parsed = JSON.parse(cachedInsights);
        setInsights(parsed);
        setFilteredInsights(parsed.filter((i: Insight) => i.significance_score >= 0.7));
      }
      if (cachedThoughts) {
        setLLMThoughts(JSON.parse(cachedThoughts));
      }
      if (cachedCategories) {
        setDetectedCategories(JSON.parse(cachedCategories));
      }
      return !!(cachedInsights || cachedThoughts);
    } catch (e) {
      console.warn('Failed to load cached data', e);
      return false;
    }
  };

  const saveToCache = async (userId: string, insights: Insight[], thoughts: LLMThought[], categories: string[]) => {
    try {
      await AsyncStorage.setItem(CACHE_KEYS.insights(userId), JSON.stringify(insights));
      await AsyncStorage.setItem(CACHE_KEYS.thoughts(userId), JSON.stringify(thoughts));
      await AsyncStorage.setItem(CACHE_KEYS.categories(userId), JSON.stringify(categories));
    } catch (e) {
      console.warn('Failed to save cached data', e);
    }
  };

  useEffect(() => {
    // Filter insights based on selected category and significance score
    let filtered = insights;
    
    // Filter out insights below 70% significance score
    filtered = filtered.filter(i => i.significance_score >= 0.7);
    
    if (selectedCategory === 'all') {
      setFilteredInsights(filtered);
    } else {
      // Handle both category and group filtering
      setFilteredInsights(filtered.filter(i => 
        i.category === selectedCategory || 
        (i.time_context?.group && i.time_context.group === selectedCategory)
      ));
    }
  }, [selectedCategory, insights]);

  const refreshFromAPI = async (userId: string, showLoader: boolean = true) => {
    if (showLoader) setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/insights`, null, {
        params: { user_id: userId, limit: 20 }
      });
      const insightsData = response.data.insights;
      setInsights(insightsData);
      
      // Extract unique categories from LLM-generated insights
      const categories = ['all']; // Always include 'all'
      const uniqueGroups = new Set();
      
      insightsData.forEach((insight: Insight) => {
        if (insight.time_context?.group) {
          uniqueGroups.add(insight.time_context.group);
        }
        // Also add the main category
        if (insight.category && !categories.includes(insight.category)) {
          categories.push(insight.category);
        }
      });
      
      // Add LLM-detected groups
      uniqueGroups.forEach((group: unknown) => {
        const groupStr = String(group);
        if (!categories.includes(groupStr)) {
          categories.push(groupStr);
        }
      });
      
      setDetectedCategories(categories);
      setFilteredInsights(insightsData);
      // Load LLM thoughts based on insights
      const thoughts = await loadLLMThoughts(userId, insightsData);
      await saveToCache(userId, insightsData, thoughts || [], categories);
      // Also save to DB for cross-device persistence
      await axios.post(`${API_URL}/insights/save`, { user_id: userId, insights: insightsData }).catch(() => null);
      if (thoughts?.length) {
        await axios.post(`${API_URL}/llm-thoughts/save`, { user_id: userId, insights: thoughts }).catch(() => null);
      }
    } catch (error) {
      console.error('Error loading insights:', error);
      Alert.alert('Error', 'Failed to load insights');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    if (user) {
      await refreshFromAPI(user.id, false);
    }
    setRefreshing(false);
  };

  const loadLLMThoughts = async (userId: string, insights: Insight[]) => {
    if (insights.length === 0) return;
    
    setLoadingThoughts(true);
    try {
      const response = await axios.post(`${API_URL}/llm-thoughts`, {
        user_id: userId,
        insights: insights
      });
      const thoughts = response.data.thoughts;
      setLLMThoughts(thoughts);
      return thoughts;
    } catch (error) {
      console.error('Error loading LLM thoughts:', error);
      Alert.alert('Error', 'Failed to load AI thoughts');
    } finally {
      setLoadingThoughts(false);
    }
  };

  const submitFeedback = async (insightId: string | undefined, feedbackType: string) => {
    if (!user || !insightId) return;
    try {
      await axios.post(`${API_URL}/insights/feedback`, null, {
        params: {
          user_id: user.id,
          insight_id: insightId,
          feedback_type: feedbackType
        }
      });
      Alert.alert('Thanks!', 'Feedback recorded');
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const closeInsightDetail = () => {
    Animated.timing(translateY, {
      toValue: 500,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setSelectedInsight(null);
      translateY.setValue(0);
    });
  };

  const closeThoughtDetail = () => {
    Animated.timing(translateY, {
      toValue: 500,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      setSelectedThought(null);
      translateY.setValue(0);
    });
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'urgent': return <AlertTriangle size={20} color="#ef4444" />;
      case 'milestone': return <Star size={20} color="#f59e0b" />;
      case 'trending': return <TrendingUp size={20} color="#10b981" />;
      case 'important': return <Zap size={20} color="#8b5cf6" />;
      default: return <Brain size={20} color={Colors[colorScheme ?? 'dark'].tint} />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'urgent': return '#ef4444';
      case 'milestone': return '#f59e0b';
      case 'trending': return '#10b981';
      case 'important': return '#8b5cf6';
      default: return Colors[colorScheme ?? 'dark'].tint;
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />
        <LinearGradient
          colors={['#0f172a', '#020617', '#000000']}
          style={StyleSheet.absoluteFill}
        />
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#9333ea" />
            <Text style={[styles.loadingText, { color: '#fff' }]}>
              Analyzing your life patterns...
            </Text>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient
        colors={['#0f172a', '#020617', '#000000']}
        style={StyleSheet.absoluteFill}
      />
      <SafeAreaView style={styles.safeArea}>
        <KnowledgeHeader
          onRefresh={onRefresh}
          refreshing={refreshing}
          onSearchToggle={() => setShowSearch(!showSearch)}
        />

        <ScrollView 
          style={styles.content} 
          showsVerticalScrollIndicator={false}
        >
          <CategoryFilter
            categories={detectedCategories}
            selectedCategory={selectedCategory}
            onSelectCategory={setSelectedCategory}
            getCategoryColor={getCategoryColor}
          />
          
          {filteredInsights.length === 0 ? (
            <View style={styles.emptyState}>
              <Brain size={48} color="#ffffff40" />
              <Text style={[
                styles.emptyStateTitle,
                { color: '#fff' }
              ]}>
                No insights yet
              </Text>
              <Text style={[
                styles.emptyStateSubtitle,
                { color: '#ffffff60' }
              ]}>
                Upload more data to generate insights about your life
              </Text>
            </View>
          ) : (
            <View>
              <Text style={[
                styles.sectionTitle, { color: '#fff' }]}>
Insights
              </Text>
              <ScrollView 
                horizontal 
                showsHorizontalScrollIndicator={false}
                style={styles.insightsHorizontalScroll}
                contentContainerStyle={styles.insightsHorizontalContainer}
              >
                {filteredInsights.map((insight) => (
                  <InsightCard
                    key={insight.id}
                    insight={insight}
                    onPress={() => {
                      setSelectedInsight(insight);
                      translateY.setValue(0);
                    }}
                    getCategoryIcon={getCategoryIcon}
                    getCategoryColor={getCategoryColor}
                  />
                ))}
              </ScrollView>
            </View>
          )}
          
          {llmThoughts.length > 0 && (
            <View>
              <Text style={[
                styles.sectionTitle, { color: '#fff' }]}>
Thoughts
              </Text>
              <ScrollView 
                horizontal 
                showsHorizontalScrollIndicator={false}
                style={styles.insightsHorizontalScroll}
                contentContainerStyle={styles.insightsHorizontalContainer}
              >
                {llmThoughts.map((thought) => (
                  <LLMThoughtCard
                    key={thought.id}
                    thought={thought}
                    onPress={() => {
                      setSelectedThought(thought);
                      translateY.setValue(0);
                    }}
                  />
                ))}
              </ScrollView>
            </View>
          )}
          
          {loadingThoughts && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#9333ea" />
              <Text style={[styles.loadingText, { color: '#fff' }]}>
                Generating AI thoughts...
              </Text>
            </View>
          )}
        </ScrollView>

        {(selectedInsight || selectedDocument || selectedThought) && (
          <View style={styles.overlay} />
        )}

        {selectedInsight && (
          <InsightDetailModal
            insight={selectedInsight}
            translateY={translateY}
            onClose={closeInsightDetail}
            getCategoryIcon={getCategoryIcon}
            getCategoryColor={getCategoryColor}
            onSourcePress={(source) => setSelectedDocument(source)}
            onFeedback={submitFeedback}
            onChatWithContext={(contentType, contentId, title, content) => handleChatWithContext(router, user, contentType, contentId, title, content, closeInsightDetail)}
          />
        )}

        {selectedDocument && (
          <DocumentModal
            document={selectedDocument}
            onClose={() => setSelectedDocument(null)}
          />
        )}

        {selectedThought && (
          <LLMThoughtModal
            thought={selectedThought}
            translateY={translateY}
            onClose={closeThoughtDetail}
            onFeedback={submitFeedback}
            onChatWithContext={(contentType, contentId, title, content) => handleChatWithContext(router, user, contentType, contentId, title, content, closeThoughtDetail)}
          />
        )}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  content: {
    flex: 1,
    paddingHorizontal: 0,
    paddingTop: 0,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 8,
    paddingHorizontal: 20,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  emptyStateSubtitle: {
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 40,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    zIndex: 999,
  },
  insightsHorizontalScroll: {
    marginVertical: 0,
  },
  insightsHorizontalContainer: {
    paddingLeft: 20,
    paddingRight: 20,
  },
});
