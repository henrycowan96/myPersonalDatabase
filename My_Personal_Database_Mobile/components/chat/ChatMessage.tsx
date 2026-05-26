import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
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
  if (message.role === 'user') {
    return (
      <View style={styles.messageRow}>
        <View style={styles.userBubble}>
          <Text style={styles.userText}>{message.content}</Text>
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
                  <MessageCircle size={12} color="#6b7280" />
                  <Text style={styles.routingBadgeText}>General conversation</Text>
                </>
              ) : (
                <>
                  <Database size={12} color="#8b5cf6" />
                  <Text style={styles.routingBadgeText}>Knowledge base search</Text>
                </>
              )}
            </View>
          )}
          <Text style={styles.assistantText}>{stripMarkdown(message.content)}</Text>
          {message.sources && message.sources.length > 0 && (
            <View style={styles.sourceSection}>
              <Text style={styles.sourceLabel}>Sources</Text>
              {message.sources.map((source: Source, sIdx: number) => (
                <TouchableOpacity
                  key={sIdx}
                  style={styles.sourceCard}
                  onPress={() => onSourcePress(source)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.sourceText} numberOfLines={2}>
                    {stripHtml(source.content)}
                  </Text>
                  <View style={styles.sourceMeta}>
                    <FileText size={11} color="#8b5cf6" />
                    <Text style={styles.sourceFilename}>
                      {getSourceTitle(source)}
                    </Text>
                    <ChevronRight size={12} color="#6b7280" style={styles.chevron} />
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
    marginBottom: 20,
  },
  userBubble: {
    backgroundColor: '#8b5cf6',
    maxWidth: '80%',
    borderRadius: 20,
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginLeft: 'auto',
  },
  userText: {
    color: '#fff',
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '500',
  },
  assistantBubble: {
    maxWidth: '90%',
  },
  assistantContent: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    padding: 16,
  },
  routingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    marginBottom: 12,
    alignSelf: 'flex-start',
    gap: 6,
  },
  routingBadgeText: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '500',
  },
  assistantText: {
    color: '#e5e7eb',
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '400',
  },
  sourceSection: {
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  sourceLabel: {
    color: '#9ca3af',
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  sourceCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    padding: 12,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
  },
  sourceText: {
    color: '#d1d5db',
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 8,
  },
  sourceMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  sourceFilename: {
    color: '#8b5cf6',
    fontSize: 12,
    fontWeight: '500',
    flex: 1,
  },
  chevron: {
    marginLeft: 4,
  },
});
