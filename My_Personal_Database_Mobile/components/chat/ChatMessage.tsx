import React, { useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native';
import { MessageCircle, Database, FileText, ChevronRight } from 'lucide-react-native';
import { stripMarkdown, stripHtml } from '../../utils/textUtils';

interface Source {
  content: string;
  metadata: any;
}

interface ChatMessageProps {
  message: {
    role: string;
    content: string;
    sources?: Source[];
    routing_decision?: string;
  };
  onSourcePress: (source: Source) => void;
  getSourceTitle: (source: Source) => string;
}

export default function ChatMessage({ message, onSourcePress, getSourceTitle }: ChatMessageProps) {
  const slideAnim = useRef(new Animated.Value(30)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.95)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 400,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 400,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 50,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  if (message.role === 'user') {
    return (
      <Animated.View style={[styles.messageRow, { transform: [{ translateX: slideAnim }], opacity: fadeAnim }]}>
        <Animated.View style={[styles.userBubble, { transform: [{ scale: scaleAnim }] }]}>
          <Text style={styles.userText}>{message.content}</Text>
        </Animated.View>
      </Animated.View>
    );
  }

  return (
    <Animated.View style={[styles.messageRow, { transform: [{ translateX: slideAnim }], opacity: fadeAnim }]}>
      <Animated.View style={[styles.assistantBubble, { transform: [{ scale: scaleAnim }] }]}>
        <View style={styles.assistantContent}>
          {message.routing_decision && (
            <Animated.View style={styles.routingBadge}>
              {message.routing_decision === 'general' ? (
                <>
                  <MessageCircle size={12} color="#94a3b8" strokeWidth={2} />
                  <Text style={styles.routingBadgeText}>General conversation</Text>
                </>
              ) : (
                <>
                  <Database size={12} color="#8b5cf6" strokeWidth={2} />
                  <Text style={styles.routingBadgeText}>Knowledge base search</Text>
                </>
              )}
            </Animated.View>
          )}
          <Text style={styles.assistantText}>{stripMarkdown(message.content)}</Text>
          {message.sources && message.sources.length > 0 && (
            <View style={styles.sourceSection}>
              <Text style={styles.sourceLabel}>Sources</Text>
              {message.sources.map((source: Source, sIdx: number) => (
                <AnimatedSourceCard
                  key={sIdx}
                  source={source}
                  onPress={() => onSourcePress(source)}
                  getSourceTitle={getSourceTitle}
                  index={sIdx}
                />
              ))}
            </View>
          )}
        </View>
      </Animated.View>
    </Animated.View>
  );
}

function AnimatedSourceCard({ source, onPress, getSourceTitle, index }: { source: Source; onPress: () => void; getSourceTitle: (s: Source) => string; index: number }) {
  const slideAnim = useRef(new Animated.Value(20)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const delay = index * 100;
    setTimeout(() => {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    }, delay);
  }, [index]);

  return (
    <Animated.View style={{ transform: [{ translateX: slideAnim }], opacity: fadeAnim }}>
      <TouchableOpacity
        style={styles.sourceCard}
        onPress={onPress}
        activeOpacity={0.7}
      >
        <Text style={styles.sourceText} numberOfLines={2}>
          {stripHtml(source.content)}
        </Text>
        <View style={styles.sourceMeta}>
          <FileText size={11} color="#8b5cf6" strokeWidth={2} />
          <Text style={styles.sourceFilename}>
            {getSourceTitle(source)}
          </Text>
          <ChevronRight size={12} color="#64748b" strokeWidth={2} style={styles.chevron} />
        </View>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  messageRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  userBubble: {
    backgroundColor: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    maxWidth: '80%',
    borderRadius: 24,
    paddingVertical: 14,
    paddingHorizontal: 18,
    marginLeft: 'auto',
    shadowColor: '#8b5cf6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 4,
  },
  userText: {
    color: '#ffffff',
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '500',
  },
  assistantBubble: {
    maxWidth: '90%',
  },
  assistantContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  routingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.12)',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 10,
    marginBottom: 14,
    alignSelf: 'flex-start',
    gap: 7,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.2)',
  },
  routingBadgeText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: '500',
    letterSpacing: 0.2,
  },
  assistantText: {
    color: '#f1f5f9',
    fontSize: 15,
    lineHeight: 23,
    fontWeight: '400',
  },
  sourceSection: {
    marginTop: 18,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  sourceLabel: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  sourceCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    padding: 14,
    borderRadius: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 1,
  },
  sourceText: {
    color: '#cbd5e1',
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 10,
  },
  sourceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  sourceFilename: {
    color: '#a78bfa',
    fontSize: 12,
    fontWeight: '500',
    flex: 1,
  },
  chevron: {
    marginLeft: 4,
  },
});
