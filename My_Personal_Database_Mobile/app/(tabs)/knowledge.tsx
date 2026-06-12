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
  TouchableOpacity,
} from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { LinearGradient } from 'expo-linear-gradient';
import { Brain, AlertTriangle, Star, TrendingUp, Zap, RefreshCw, ChevronRight } from 'lucide-react-native';
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
import LoadingScreen from '../../components/LoadingScreen';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';
const { width } = Dimensions.get('window');

// Make function globally available
declare global {
  var handleChatWithContext: (router: any, user: User | null, contentType: string, contentId: string, title: string, content: string, onClose?: () => void) => Promise<void>;
}

const handleChatWithContext = async (router: any, user: User | null, contentType: string, contentId: string, title: string, content: string, onClose?: () => void, setCreatingChatContext?: (loading: boolean) => void) => {
  console.log('handleChatWithContext called!', { router, user, contentType, contentId, title, API_URL });
  if (setCreatingChatContext) setCreatingChatContext(true);
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
  } finally {
    if (setCreatingChatContext) setCreatingChatContext(false);
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
  const [loadingDB, setLoadingDB] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [creatingChatContext, setCreatingChatContext] = useState(false);
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
  const [showAllInsights, setShowAllInsights] = useState(false);
  const [showAllThoughts, setShowAllThoughts] = useState(false);
  const colorScheme = useColorScheme();

  const filterStaleThoughts = (thoughts: LLMThought[]): LLMThought[] => {
    if (thoughts.length === 0) return thoughts;

    // Find the most recent generation timestamp
    const mostRecentTimestamp = thoughts.reduce((latest, thought) => {
      const thoughtDate = new Date(thought.generated_at);
      return thoughtDate > latest ? thoughtDate : latest;
    }, new Date(thoughts[0].generated_at));

    // Only include thoughts from the most recent run (within 1 hour window)
    const oneHourMs = 60 * 60 * 1000;
    return thoughts.filter(thought => {
      const thoughtDate = new Date(thought.generated_at);
      const timeDiff = Math.abs(mostRecentTimestamp.getTime() - thoughtDate.getTime());
      return timeDiff <= oneHourMs;
    });
  };

  const cleanCategoryName = (category: string): string => {
    return category
      .replace(/[_-]/g, ' ')    // Replace underscores and hyphens with spaces first
      .replace(/[#*`~]/g, '')   // Remove other markdown special characters
      .replace(/\s+/g, ' ')     // Replace multiple spaces with single space
      .trim();                  // Remove leading/trailing spaces
  };
  
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
    setLoading(true);
    // Try DB first (persistent across devices), then AsyncStorage (offline fallback)
    const hasData = await loadFromDB(userId);
    if (!hasData) {
      await loadFromCache(userId);
    }
    setLoading(false);
    // NOTE: We intentionally do NOT auto-refresh from API here.
    // Insights are regenerated in the background after data upload.
    // Users can manually refresh via pull-to-refresh.
  };

  const loadFromDB = async (userId: string): Promise<boolean> => {
    setLoadingDB(true);
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
        setLLMThoughts(filterStaleThoughts(thoughtsRes.data.thoughts));
        hasThoughts = true;
      }

      return hasInsights || hasThoughts;
    } catch (e) {
      console.warn('Failed to load from DB', e);
      return false;
    } finally {
      setLoadingDB(false);
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
        setLLMThoughts(filterStaleThoughts(JSON.parse(cachedThoughts)));
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
      setLLMThoughts(filterStaleThoughts(thoughts));
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
    setSubmittingFeedback(true);
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
      Alert.alert('Error', 'Failed to submit feedback');
    } finally {
      setSubmittingFeedback(false);
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
    return <Brain size={20} color="#fff" />;
  };

  const getCategoryColor = (category: string) => {
    return '#9333ea';
  };

  if (loading) {
    return <LoadingScreen message="Loading your insights..." subtext="Retrieving from database" />;
  }

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
          <Text style={styles.title}>Knowledge</Text>
          <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
            <RefreshCw size={20} color="#9333ea" />
          </TouchableOpacity>
        </View>

        <ScrollView 
          style={styles.content} 
          showsVerticalScrollIndicator={false}
        >
          {/* Category Filter */}
          <View style={styles.section}>
            <Text style={styles.sectionHeader}>CATEGORIES</Text>
            <ScrollView 
              horizontal 
              showsHorizontalScrollIndicator={false}
              style={styles.categoryScroll}
              contentContainerStyle={styles.categoryContainer}
            >
              {detectedCategories.map((category) => (
                <TouchableOpacity
                  key={category}
                  onPress={() => setSelectedCategory(category)}
                  style={[
                    styles.categoryChip,
                    selectedCategory === category && styles.categoryChipActive
                  ]}
                >
                  <Text style={[
                    styles.categoryChipText,
                    selectedCategory === category && styles.categoryChipTextActive
                  ]}>
                    {cleanCategoryName(category).toUpperCase()}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
          
          {loadingDB ? (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>INSIGHTS</Text>
              <View style={styles.sectionCard}>
                {[1, 2, 3].map((i) => (
                  <View key={i} style={styles.insightItem}>
                    <View style={styles.insightItemContent}>
                      <View style={[styles.insightIconContainer, styles.skeleton]} />
                      <View style={styles.insightTextContainer}>
                        <View style={[styles.skeletonTitle, styles.skeleton]} />
                        <View style={[styles.skeletonDescription, styles.skeleton]} />
                        <View style={[styles.skeletonMeta, styles.skeleton]} />
                      </View>
                      <View style={[styles.skeletonChevron, styles.skeleton]} />
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ) : filteredInsights.length === 0 && !loading ? (
            <View style={styles.emptyState}>
              <View style={styles.emptyIconContainer}>
                <LinearGradient
                  colors={['#9333ea', '#9333eacc']}
                  style={styles.emptyIconGradient}
                >
                  <Brain size={48} color="#fff" />
                </LinearGradient>
              </View>
              <Text style={styles.emptyTitle}>No insights yet</Text>
              <Text style={styles.emptySubtitle}>
                Upload more data to generate insights about your life
              </Text>
            </View>
          ) : (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>INSIGHTS</Text>
              <View style={styles.sectionCard}>
                {(showAllInsights ? filteredInsights : filteredInsights.slice(0, 3)).map((insight) => (
                  <TouchableOpacity
                    key={insight.id}
                    onPress={() => {
                      setSelectedInsight(insight);
                      translateY.setValue(0);
                    }}
                    style={styles.insightItem}
                  >
                    <View style={styles.insightItemContent}>
                      <View style={styles.insightIconContainer}>
                        <LinearGradient
                          colors={[getCategoryColor(insight.category), `${getCategoryColor(insight.category)}cc`]}
                          style={styles.insightIconGradient}
                        >
                          {getCategoryIcon(insight.category)}
                        </LinearGradient>
                      </View>
                      <View style={styles.insightTextContainer}>
                        <Text style={styles.insightTitle}>{insight.title}</Text>
                        <Text style={styles.insightDescription} numberOfLines={2}>
                          {insight.description}
                        </Text>
                      </View>
                      <ChevronRight size={20} color="#475569" />
                    </View>
                  </TouchableOpacity>
                ))}
                {filteredInsights.length > 3 && (
                  <TouchableOpacity
                    onPress={() => setShowAllInsights(!showAllInsights)}
                    style={styles.seeMoreButton}
                  >
                    <Text style={styles.seeMoreText}>
                      {showAllInsights ? 'See Less' : `See More (${filteredInsights.length - 3} more)`}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}
          
          {llmThoughts.length > 0 && (
            <View style={styles.section}>
              <Text style={styles.sectionHeader}>AI THOUGHTS</Text>
              <View style={styles.sectionCard}>
                {(showAllThoughts ? llmThoughts : llmThoughts.slice(0, 3)).map((thought) => (
                  <TouchableOpacity
                    key={thought.id}
                    onPress={() => {
                      setSelectedThought(thought);
                      translateY.setValue(0);
                    }}
                    style={styles.insightItem}
                  >
                    <View style={styles.insightItemContent}>
                      <View style={styles.insightIconContainer}>
                        <LinearGradient
                          colors={['#9333ea', '#9333eacc']}
                          style={styles.insightIconGradient}
                        >
                          <Brain size={20} color="#fff" />
                        </LinearGradient>
                      </View>
                      <View style={styles.insightTextContainer}>
                        <Text style={styles.insightTitle}>{cleanCategoryName(thought.title)}</Text>
                        <Text style={styles.insightDescription} numberOfLines={2}>
                          {cleanCategoryName(thought.content)}
                        </Text>
                      </View>
                      <ChevronRight size={20} color="#475569" />
                    </View>
                  </TouchableOpacity>
                ))}
                {llmThoughts.length > 3 && (
                  <TouchableOpacity
                    onPress={() => setShowAllThoughts(!showAllThoughts)}
                    style={styles.seeMoreButton}
                  >
                    <Text style={styles.seeMoreText}>
                      {showAllThoughts ? 'See Less' : `See More (${llmThoughts.length - 3} more)`}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}
          
          {loadingThoughts && (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#9333ea" />
              <Text style={styles.loadingText}>
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
            onChatWithContext={(contentType, contentId, title, content) => handleChatWithContext(router, user, contentType, contentId, title, content, closeInsightDetail, setCreatingChatContext)}
            submittingFeedback={submittingFeedback}
            creatingChatContext={creatingChatContext}
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
            onChatWithContext={(contentType, contentId, title, content) => handleChatWithContext(router, user, contentType, contentId, title, content, closeThoughtDetail, setCreatingChatContext)}
            submittingFeedback={submittingFeedback}
            creatingChatContext={creatingChatContext}
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
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
  },
  content: {
    flex: 1,
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
  categoryScroll: {
    paddingHorizontal: 16,
  },
  categoryContainer: {
    paddingHorizontal: 8,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    marginRight: 8,
  },
  categoryChipActive: {
    backgroundColor: 'rgba(147, 51, 234, 0.2)',
    borderColor: 'rgba(147, 51, 234, 0.5)',
  },
  categoryChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#94a3b8',
  },
  categoryChipTextActive: {
    color: '#9333ea',
  },
  insightItem: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  insightItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  insightIconContainer: {
    marginRight: 16,
  },
  insightIconGradient: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightTextContainer: {
    flex: 1,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  insightDescription: {
    fontSize: 13,
    fontWeight: '400',
    color: '#64748b',
    marginBottom: 8,
  },
  insightMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  insightCategory: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9333ea',
    marginRight: 12,
  },
  insightScore: {
    fontSize: 11,
    fontWeight: '500',
    color: '#64748b',
  },
  seeMoreButton: {
    padding: 16,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.05)',
  },
  seeMoreText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#9333ea',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#fff',
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: '#64748b',
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
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  emptyIconGradient: {
    width: 100,
    height: 100,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
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
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    zIndex: 999,
  },
  skeleton: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 8,
  },
  skeletonTitle: {
    height: 20,
    width: '70%',
    marginBottom: 8,
  },
  skeletonDescription: {
    height: 14,
    width: '90%',
    marginBottom: 8,
  },
  skeletonMeta: {
    height: 12,
    width: '40%',
  },
  skeletonChevron: {
    width: 20,
    height: 20,
  },
});
