import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, PanResponder, ScrollView } from 'react-native';
import { X, ThumbsUp, ThumbsDown, MessageSquare, MessageCircle, Brain } from 'lucide-react-native';
import { formatCategoryName } from '../../utils/textUtils';

function cleanMarkdown(text: string): string {
  return text
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/#{1,6}\s+(.*)/g, '$1')
    .replace(/`{1,3}(.*?)`{1,3}/g, '$1')
    .replace(/\|/g, ' ')
    .replace(/\n[-=]{3,}/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

interface LLMThought {
  id: string;
  thought_type: string;
  title: string;
  content: string;
  prompt_used: string;
  generated_at: string;
}

interface LLMThoughtModalProps {
  thought: LLMThought;
  translateY: Animated.Value;
  onClose: () => void;
  onFeedback?: (thoughtId: string, feedbackType: string) => void;
  onChatWithContext?: (contentType: string, contentId: string, title: string, content: string) => void;
}

export default function LLMThoughtModal({ thought, translateY, onClose, onFeedback, onChatWithContext }: LLMThoughtModalProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);

  const handleFeedback = (type: string) => {
    setFeedbackGiven(type);
    onFeedback?.(thought.id, type);
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
          <Brain size={24} color="#9333ea" />
        </View>
        <Text style={[
          styles.detailTitle,
          { color: '#fff' }
        ]}>
          {thought.title}
        </Text>
        <View style={styles.headerButtons}>
          <TouchableOpacity
            style={styles.chatButton}
            onPress={() => {
              console.log('Chat button pressed!', { thought, onChatWithContext });
              onChatWithContext?.('thought', thought.thought_type, thought.title, thought.content);
            }}
          >
            <MessageCircle size={20} color="#9333ea" />
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
          { color: '#9333ea' }
        ]}>
          {formatCategoryName(thought.thought_type)}
        </Text>

        <Text style={[
          styles.detailDescription,
          { color: '#ffffffcc' }
        ]}>
          {cleanMarkdown(thought.content)}
        </Text>

        <View style={styles.sourcesSection}>
          <Text style={[
            styles.sourcesLabel,
            { color: '#fff' }
          ]}>
            Generated based on your insights
          </Text>
          <Text style={[
            styles.sourceItemText,
            { color: '#ffffff80', marginTop: 8 }
          ]}>
            This AI thought was generated using advanced language models based on your personal insights and patterns.
          </Text>
        </View>

        {onFeedback && (
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
              >
                <ThumbsUp size={20} color={feedbackGiven === 'helpful' ? '#fff' : '#10b981'} />
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.feedbackButton,
                  feedbackGiven === 'not_helpful' && styles.feedbackButtonDown
                ]}
                onPress={() => handleFeedback('not_helpful')}
              >
                <ThumbsDown size={20} color={feedbackGiven === 'not_helpful' ? '#fff' : '#ef4444'} />
              </TouchableOpacity>
            </View>
          </View>
        )}
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
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
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
  scrollContent: {
    flex: 1,
    marginTop: 8,
  },
  sourcesSection: {
    marginBottom: 20,
  },
  sourcesLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  sourceItemText: {
    fontSize: 14,
  },
  feedbackSection: {
    marginTop: 20,
    marginBottom: 20,
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
