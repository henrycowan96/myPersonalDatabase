import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Brain, Clock } from 'lucide-react-native';
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

interface LLMThoughtCardProps {
  thought: LLMThought;
  onPress: () => void;
}

export default function LLMThoughtCard({ thought, onPress }: LLMThoughtCardProps) {
  return (
    <TouchableOpacity
      style={[
        styles.llmThoughtCard,
        { backgroundColor: 'rgba(147, 51, 234, 0.1)', borderColor: 'rgba(147, 51, 234, 0.3)' }
      ]}
      onPress={onPress}
    >
      <View style={styles.llmThoughtHeader}>
        <View style={styles.llmThoughtIconContainer}>
          <Brain size={20} color="#9333ea" />
        </View>
        <View style={styles.llmThoughtTitleContainer}>
          <Text style={[styles.llmThoughtType, { color: '#ffffff80' }]}>
            {formatCategoryName(thought.thought_type)}
          </Text>
          <Text style={[styles.llmThoughtTitle, { color: '#fff' }]}>
            {thought.title}
          </Text>
        </View>
      </View>
      
      <Text style={[styles.llmThoughtContent, { color: '#ffffffcc' }]} numberOfLines={3}>
        {cleanMarkdown(thought.content)}
      </Text>
      
      <View style={styles.llmThoughtFooter}>
        <Clock size={12} color="#ffffff60" />
        <Text style={[styles.llmThoughtTime, { color: '#ffffff60' }]}>
          {new Date(thought.generated_at).toLocaleDateString()}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  llmThoughtCard: {
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
  llmThoughtHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  llmThoughtIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  llmThoughtTitleContainer: {
    flex: 1,
  },
  llmThoughtTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  llmThoughtType: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  llmThoughtContent: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  llmThoughtFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  llmThoughtTime: {
    fontSize: 11,
  },
});
