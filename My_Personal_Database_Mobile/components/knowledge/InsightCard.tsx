import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Brain, AlertTriangle, Star, TrendingUp, Zap, Clock, FileText } from 'lucide-react-native';
import { formatCategoryName } from '../../utils/textUtils';

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

interface InsightCardProps {
  insight: Insight;
  onPress: () => void;
  getCategoryIcon: (category: string) => React.ReactNode;
  getCategoryColor: (category: string) => string;
}

export default function InsightCard({ insight, onPress, getCategoryIcon, getCategoryColor }: InsightCardProps) {
  return (
    <TouchableOpacity
      style={[
        styles.insightCard,
        { backgroundColor: 'rgba(147, 51, 234, 0.1)', borderColor: 'rgba(147, 51, 234, 0.3)' }
      ]}
      onPress={onPress}
    >
      <View style={styles.insightHeader}>
        <View style={styles.insightIconContainer}>
          {getCategoryIcon(insight.category)}
        </View>
        <View style={styles.insightTitleContainer}>
          <Text style={[styles.insightCategory, { color: '#ffffff80' }]}>
            {insight.category ? formatCategoryName(insight.category) : 'Unknown'}
          </Text>
          <Text style={[styles.insightTitle, { color: '#fff' }]}>
            {insight.title}
          </Text>
        </View>
      </View>

      <Text style={[styles.insightDescription, { color: '#ffffffcc' }]} numberOfLines={3}>
        {insight.description}
      </Text>

      {insight.actionable && (
        <View style={styles.actionableBadge}>
          <Zap size={12} color="#f59e0b" />
          <Text style={styles.actionableText}>Actionable</Text>
        </View>
      )}

      <View style={styles.insightFooter}>
        <Clock size={12} color="#ffffff60" />
        <Text style={[styles.insightTime, { color: '#ffffff60' }]}>
          {new Date(insight.detected_at).toLocaleDateString()}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  insightCard: {
    borderRadius: 16,
    padding: 16,
    marginRight: 12,
    marginBottom: 12,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    width: 300,
    height: 220,
  },
  insightHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  insightIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  insightTitleContainer: {
    flex: 1,
  },
  insightCategory: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  insightTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  insightDescription: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  actionableBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  actionableText: {
    color: '#f59e0b',
    fontSize: 11,
    fontWeight: '600',
    marginLeft: 4,
  },
  insightFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  insightTime: {
    fontSize: 11,
  },
});
