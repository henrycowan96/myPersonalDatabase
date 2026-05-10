import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MessageCircle, Database, FileText } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { stripMarkdown } from '../../utils/textUtils';

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
  if (message.role === 'user') {
    return (
      <View style={styles.messageRow}>
        <View style={styles.messageBubble}>
          <LinearGradient
            colors={['#7c3aed', '#4f46e5']}
            style={styles.userGradient}
          >
            <Text style={styles.userText}>{message.content}</Text>
          </LinearGradient>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.messageRow}>
      <View style={styles.assistantBubble}>
        <View style={styles.assistantContent}>
          {message.routing_decision && (
            <View style={styles.routingBadge}>
              {message.routing_decision === 'general' ? (
                <>
                  <MessageCircle size={10} color="#64748b" />
                  <Text style={styles.routingBadgeText}>General Conversation</Text>
                </>
              ) : (
                <>
                  <Database size={10} color="#9333ea" />
                  <Text style={styles.routingBadgeText}>Knowledge Base Search</Text>
                </>
              )}
            </View>
          )}
          <Text style={styles.assistantText}>{stripMarkdown(message.content)}</Text>
          {message.sources && message.sources.length > 0 && (
            <View style={styles.sourceSection}>
              <Text style={styles.sourceLabel}>VERIFIED SOURCES</Text>
              {message.sources.map((source: Source, sIdx: number) => (
                <TouchableOpacity
                  key={sIdx}
                  style={styles.sourceCard}
                  onPress={() => onSourcePress(source)}
                >
                  <Text style={styles.sourceText} numberOfLines={2}>
                    "{source.content}"
                  </Text>
                  <View style={styles.sourceMeta}>
                    <FileText size={10} color="#9333ea" />
                    <Text style={styles.sourceFilename}>
                      {getSourceTitle(source)}
                    </Text>
                  </View>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  messageRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  messageBubble: {
    maxWidth: '85%',
    borderRadius: 24,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  userGradient: {
    padding: 16,
  },
  userText: {
    color: '#fff',
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '600',
  },
  assistantBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  assistantContent: {
    padding: 16,
  },
  routingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    marginBottom: 12,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  routingBadgeText: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '600',
    marginLeft: 4,
    letterSpacing: 0.5,
  },
  assistantText: {
    color: '#cbd5e1',
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '500',
  },
  sourceSection: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.05)',
  },
  sourceLabel: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 12,
  },
  sourceCard: {
    backgroundColor: 'rgba(0,0,0,0.2)',
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.03)',
  },
  sourceText: {
    color: '#94a3b8',
    fontSize: 12,
    fontStyle: 'italic',
    lineHeight: 18,
  },
  sourceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  sourceFilename: {
    color: '#9333ea',
    fontSize: 10,
    fontWeight: 'bold',
    marginLeft: 6,
  },
});
