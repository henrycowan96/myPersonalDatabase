import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { supabase } from '../../lib/supabase';
import axios from 'axios';
import { LinearGradient } from 'expo-linear-gradient';
import {
  ArrowRightLeft,
  RotateCcw,
  MapPin,
  Briefcase,
  Heart,
  Activity,
  DollarSign,
  User,
  Target,
  Repeat,
  Filter,
  Calendar,
} from 'lucide-react-native';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';
const { width } = Dimensions.get('window');

interface TimelineEvent {
  id: string;
  entity_key: string;
  entity_category: string;
  old_value: string | null;
  new_value: string;
  source_timestamp: string;
  confidence: number;
  detection_reason: string;
  is_reversion: boolean;
}

interface User {
  id?: string;
}

const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  location: { label: 'Location', icon: <MapPin size={16} color="#3b82f6" />, color: '#3b82f6' },
  work: { label: 'Work', icon: <Briefcase size={16} color="#8b5cf6" />, color: '#8b5cf6' },
  relationships: { label: 'Relationships', icon: <Heart size={16} color="#ef4444" />, color: '#ef4444' },
  health: { label: 'Health', icon: <Activity size={16} color="#10b981" />, color: '#10b981' },
  finance: { label: 'Finance', icon: <DollarSign size={16} color="#f59e0b" />, color: '#f59e0b' },
  identity: { label: 'Identity', icon: <User size={16} color="#ec4899" />, color: '#ec4899' },
  goals: { label: 'Goals', icon: <Target size={16} color="#06b6d4" />, color: '#06b6d4' },
  habits: { label: 'Habits', icon: <Repeat size={16} color="#84cc16" />, color: '#84cc16' },
};

function formatDate(isoString: string): string {
  if (!isoString) return 'Unknown date';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  } catch {
    return isoString.slice(0, 7);
  }
}

function formatYearMonth(isoString: string): string {
  if (!isoString) return 'Unknown';
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
  } catch {
    return isoString.slice(0, 7);
  }
}

function groupByYearMonth(events: TimelineEvent[]): Map<string, TimelineEvent[]> {
  const groups = new Map<string, TimelineEvent[]>();
  for (const event of events) {
    const key = formatYearMonth(event.source_timestamp);
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(event);
  }
  return groups;
}

export default function TimelineScreen() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const colorScheme = useColorScheme();

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      if (user?.id) {
        loadTimeline(user.id);
        loadCategories(user.id);
      }
    });
  }, []);

  const loadTimeline = useCallback(async (userId: string) => {
    setLoading(true);
    try {
      const params: any = { user_id: userId, limit: 100 };
      if (selectedCategory !== 'all') {
        params.category = selectedCategory;
      }
      const response = await axios.get(`${API_URL}/timeline`, { params });
      setEvents(response.data.timeline || []);
    } catch (error) {
      console.error('Error loading timeline:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  const loadCategories = useCallback(async (userId: string) => {
    try {
      const response = await axios.get(`${API_URL}/timeline/categories`, {
        params: { user_id: userId }
      });
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  }, []);

  useEffect(() => {
    if (user?.id) {
      loadTimeline(user.id);
    }
  }, [selectedCategory, user, loadTimeline]);

  const grouped = groupByYearMonth(events);
  const groupKeys = Array.from(grouped.keys());

  const renderEventCard = (event: TimelineEvent) => {
    const config = CATEGORY_CONFIG[event.entity_category] || {
      label: event.entity_category,
      icon: <ArrowRightLeft size={16} color="#9ca3af" />,
      color: '#9ca3af',
    };

    const isReversion = event.is_reversion;

    return (
      <View key={event.id} style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={[styles.categoryBadge, { backgroundColor: `${config.color}20` }]}>
            {config.icon}
            <Text style={[styles.categoryBadgeText, { color: config.color }]}>
              {config.label}
            </Text>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
            <Calendar size={12} color="#9ca3af" />
            <Text style={styles.dateText}>{formatDate(event.source_timestamp)}</Text>
          </View>
        </View>

        <View style={styles.changeRow}>
          <Text style={styles.oldValue} numberOfLines={1}>
            {event.old_value || '—'}
          </Text>
          <View style={styles.arrowContainer}>
            {isReversion ? (
              <RotateCcw size={18} color="#f59e0b" />
            ) : (
              <ArrowRightLeft size={18} color="#9ca3af" />
            )}
          </View>
          <Text style={[styles.newValue, isReversion && { color: '#f59e0b' }]} numberOfLines={1}>
            {event.new_value}
          </Text>
        </View>

        {isReversion && (
          <View style={styles.reversionBadge}>
            <RotateCcw size={12} color="#f59e0b" />
            <Text style={styles.reversionText}>Reversion</Text>
          </View>
        )}

        <Text style={styles.reasonText}>{event.detection_reason}</Text>

        <View style={styles.footer}>
          <Text style={styles.entityKey}>{event.entity_key}</Text>
          <Text style={styles.confidenceText}>
            {Math.round((event.confidence || 0) * 100)}% confidence
          </Text>
        </View>
      </View>
    );
  };

  if (loading && events.length === 0) {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" />
        <LinearGradient colors={['#0f172a', '#020617', '#000000']} style={StyleSheet.absoluteFill} />
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#9333ea" />
            <Text style={styles.loadingText}>Loading your life timeline...</Text>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <LinearGradient colors={['#0f172a', '#020617', '#000000']} style={StyleSheet.absoluteFill} />
      <SafeAreaView style={styles.safeArea}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Timeline</Text>
          <Text style={styles.headerSubtitle}>How your life has changed</Text>
        </View>

        {/* Category filter pills */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.filterScroll}
          contentContainerStyle={styles.filterContent}
        >
          <TouchableOpacity
            style={[
              styles.filterPill,
              selectedCategory === 'all' && styles.filterPillActive,
            ]}
            onPress={() => setSelectedCategory('all')}
          >
            <Filter size={14} color={selectedCategory === 'all' ? '#fff' : '#9ca3af'} />
            <Text style={[styles.filterPillText, selectedCategory === 'all' && styles.filterPillTextActive]}>
              All
            </Text>
          </TouchableOpacity>

          {categories.map((cat) => {
            const config = CATEGORY_CONFIG[cat];
            return (
              <TouchableOpacity
                key={cat}
                style={[
                  styles.filterPill,
                  selectedCategory === cat && { backgroundColor: `${config?.color || '#9333ea'}30`, borderColor: config?.color || '#9333ea' },
                ]}
                onPress={() => setSelectedCategory(cat)}
              >
                {config?.icon}
                <Text
                  style={[
                    styles.filterPillText,
                    selectedCategory === cat && { color: config?.color || '#fff', fontWeight: '700' },
                  ]}
                >
                  {config?.label || cat}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* Timeline content */}
        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {events.length === 0 ? (
            <View style={styles.emptyState}>
              <ArrowRightLeft size={48} color="#ffffff40" />
              <Text style={styles.emptyStateTitle}>No timeline events yet</Text>
              <Text style={styles.emptyStateSubtitle}>
                Upload more data to see how your life has changed over time
              </Text>
            </View>
          ) : (
            groupKeys.map((groupKey) => (
              <View key={groupKey} style={styles.groupContainer}>
                <Text style={styles.groupHeader}>{groupKey}</Text>
                <View style={styles.timelineLine} />
                {grouped.get(groupKey)?.map(renderEventCard)}
              </View>
            ))
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#fff',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 8,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#9ca3af',
    marginTop: 4,
  },
  filterScroll: {
    maxHeight: 48,
    marginBottom: 8,
  },
  filterContent: {
    paddingHorizontal: 20,
    gap: 8,
    flexDirection: 'row',
    alignItems: 'center',
  },
  filterPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  filterPillActive: {
    backgroundColor: '#9333ea30',
    borderColor: '#9333ea',
  },
  filterPillText: {
    fontSize: 13,
    color: '#9ca3af',
    fontWeight: '500',
  },
  filterPillTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 8,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 80,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginTop: 16,
  },
  emptyStateSubtitle: {
    fontSize: 14,
    color: '#9ca3af',
    textAlign: 'center',
    paddingHorizontal: 32,
    marginTop: 8,
  },
  groupContainer: {
    marginBottom: 24,
    position: 'relative',
  },
  groupHeader: {
    fontSize: 14,
    fontWeight: '700',
    color: '#9333ea',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 12,
  },
  timelineLine: {
    position: 'absolute',
    left: 8,
    top: 32,
    bottom: 0,
    width: 2,
    backgroundColor: '#334155',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    marginLeft: 24,
    borderWidth: 1,
    borderColor: '#334155',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  categoryBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  categoryBadgeText: {
    fontSize: 12,
    fontWeight: '600',
  },
  dateText: {
    fontSize: 12,
    color: '#9ca3af',
  },
  changeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  oldValue: {
    flex: 1,
    fontSize: 14,
    color: '#9ca3af',
    textDecorationLine: 'line-through',
  },
  arrowContainer: {
    paddingHorizontal: 4,
  },
  newValue: {
    flex: 1,
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  reversionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    backgroundColor: '#f59e0b20',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginBottom: 8,
  },
  reversionText: {
    fontSize: 12,
    color: '#f59e0b',
    fontWeight: '600',
  },
  reasonText: {
    fontSize: 13,
    color: '#cbd5e1',
    lineHeight: 18,
    marginBottom: 8,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#334155',
    paddingTop: 8,
  },
  entityKey: {
    fontSize: 12,
    color: '#64748b',
    textTransform: 'capitalize',
  },
  confidenceText: {
    fontSize: 12,
    color: '#64748b',
  },
});
