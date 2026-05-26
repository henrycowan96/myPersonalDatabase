import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Animated, PanResponder, ActivityIndicator } from 'react-native';
import { X, ThumbsUp, ThumbsDown, FileText, ChevronRight, MessageCircle, Loader2 } from 'lucide-react-native';
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

interface InsightDetailModalProps {
  insight: Insight;
  translateY: Animated.Value;
  onClose: () => void;
  getCategoryIcon: (category: string) => React.ReactNode;
  getCategoryColor: (category: string) => string;
  onSourcePress: (source: any) => void;
  onFeedback: (insightId: string, feedbackType: string) => void;
  onChatWithContext?: (contentType: string, contentId: string, title: string, content: string) => void;
  submittingFeedback?: boolean;
  creatingChatContext?: boolean;
}

export default function InsightDetailModal({
  insight,
  translateY,
  onClose,
  getCategoryIcon,
  getCategoryColor,
  onSourcePress,
  onFeedback,
  onChatWithContext,
  submittingFeedback = false,
  creatingChatContext = false
}: InsightDetailModalProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);

  const handleFeedback = (type: string) => {
    setFeedbackGiven(type);
    onFeedback(insight.id, type);
  };

  
  const panResponder = PanResponder.create({
    onMoveShouldSetPanResponder: (_, gestureState) => {
      return gestureState.dy > 0;
    },
    onPanResponderMove: (_, gestureState) => {
      if (gestureState.dy > 0) {
        translateY.setValue(gestureState.dy);
      }
    },
    onPanResponderRelease: (_, gestureState) => {
      if (gestureState.dy > 100) {
        onClose();
      } else {
        Animated.spring(translateY, {
          toValue: 0,
          useNativeDriver: true,
        }).start();
      }
    },
  });

  return (
    <Animated.View
      style={[
        styles.detailContainer,
        { transform: [{ translateY }] }
      ]}
      {...panResponder.panHandlers}
    >
      <View style={styles.handleIndicator} />
      
      <View style={styles.detailHeader}>
        <View style={styles.detailIconContainer}>
          {getCategoryIcon(insight.category)}
        </View>
        <Text style={[
          styles.detailTitle,
          { color: '#fff' }
        ]}>
          {insight.title}
        </Text>
        <View style={styles.headerButtons}>
          <TouchableOpacity
            style={styles.chatButton}
            onPress={() => {
              onChatWithContext?.('insight', insight.category, insight.title, insight.description);
            }}
            disabled={creatingChatContext}
          >
            {creatingChatContext ? (
              <ActivityIndicator size={20} color="#9333ea" />
            ) : (
              <MessageCircle size={20} color="#9333ea" />
            )}
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.closeButtonContainer}
            onPress={onClose}
          >
            <X size={24} color="#9333ea" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={[
          styles.detailCategory,
          { color: getCategoryColor(insight.category) }
        ]}>
          {formatCategoryName(insight.category)}
        </Text>

        <Text style={[
          styles.detailDescription,
          { color: '#ffffffcc' }
        ]}>
          {insight.description}
        </Text>

        {insight.entities.length > 0 && (
          <View style={styles.entitiesSection}>
            <Text style={[
              styles.entitiesLabel,
              { color: '#fff' }
            ]}>
              Related Entities
            </Text>
            <View style={styles.entitiesList}>
              {insight.entities.map((entity, idx) => (
                <View key={`entity-${idx}-${entity}`} style={styles.entityTag}>
                  <Text style={[
                    styles.entityTagText,
                    { color: '#fff' }
                  ]}>
                    {entity}
                  </Text>
                </View>
              ))}
            </View>
          </View>
        )}

        <View style={styles.sourcesSection}>
          <Text style={[
            styles.sourcesLabel,
            { color: '#fff' }
          ]}>
            Sources ({insight.sources.length})
          </Text>
          <View style={styles.sourcesList}>
            {insight.sources.map((source: any, idx: number) => (
              <TouchableOpacity
                key={`source-${idx}-${source}`}
                style={styles.sourceItem}
                onPress={() => onSourcePress(source)}
              >
                <FileText size={14} color="#9333ea" />
                <Text style={[
                  styles.sourceItemText,
                  { color: '#fff' }
                ]}>
                  {source.metadata?.source || 'Document'}
                </Text>
                <ChevronRight size={14} color="#ffffff80" />
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.feedbackSection}>
          <Text style={[
            styles.feedbackLabel,
              { color: '#fff' }
            ]}>
              Was this helpful?
            </Text>
          <View style={styles.feedbackButtons}>
            <TouchableOpacity
              style={[
                styles.feedbackButton,
                feedbackGiven === 'helpful' && styles.feedbackButtonUp
              ]}
              onPress={() => handleFeedback('helpful')}
              disabled={submittingFeedback}
            >
              {submittingFeedback ? (
                <ActivityIndicator size={20} color="#10b981" />
              ) : (
                <ThumbsUp size={20} color={feedbackGiven === 'helpful' ? '#fff' : '#10b981'} />
              )}
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.feedbackButton,
                feedbackGiven === 'not_helpful' && styles.feedbackButtonDown
              ]}
              onPress={() => handleFeedback('not_helpful')}
              disabled={submittingFeedback}
            >
              {submittingFeedback ? (
                <ActivityIndicator size={20} color="#ef4444" />
              ) : (
                <ThumbsDown size={20} color={feedbackGiven === 'not_helpful' ? '#fff' : '#ef4444'} />
              )}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  detailContainer: {
    position: 'absolute',
    top: 100,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
    padding: 20,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 10,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  handleIndicator: {
    width: 40,
    height: 4,
    backgroundColor: '#666',
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: 8,
    marginBottom: 16,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  detailIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  detailTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    flex: 1,
  },
  closeButtonContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailCategory: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 8,
  },
  detailDescription: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 20,
  },
  entitiesSection: {
    marginBottom: 20,
  },
  entitiesLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  entitiesList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  entityTag: {
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.2)',
  },
  entityTagText: {
    fontSize: 12,
  },
  sourcesSection: {
    marginBottom: 20,
    flex: 1,
  },
  sourcesLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  scrollContent: {
    flex: 1,
  },
  sourcesList: {
    marginBottom: 8,
  },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: 'rgba(147, 51, 234, 0.05)',
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.1)',
  },
  sourceItemText: {
    flex: 1,
    fontSize: 14,
    marginLeft: 8,
  },
  feedbackSection: {
    marginTop: 20,
  },
  feedbackLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 12,
    textAlign: 'center',
  },
  feedbackButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
  },
  feedbackButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.2)',
  },
  feedbackButtonUp: {
    backgroundColor: '#10b981',
  },
  feedbackButtonDown: {
    backgroundColor: '#ef4444',
    borderColor: '#ef4444',
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  chatButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.2)',
  },
});
