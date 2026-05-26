import React from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, Platform, KeyboardAvoidingView } from 'react-native';
import { Send } from 'lucide-react-native';

interface ChatInputProps {
  query: string;
  setQuery: (text: string) => void;
  loading: boolean;
  onSend: () => void;
}

export default function ChatInput({ query, setQuery, loading, onSend }: ChatInputProps) {
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
    >
      <View style={styles.inputArea}>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Message dhaki..."
            placeholderTextColor="#6b7280"
            value={query}
            onChangeText={setQuery}
            multiline
            maxLength={2000}
          />
        </View>
        <TouchableOpacity
          onPress={onSend}
          disabled={loading || !query.trim()}
          style={[
            styles.sendButton,
            (loading || !query.trim()) && styles.sendButtonDisabled
          ]}
        >
          <Send size={18} color={loading || !query.trim() ? '#6b7280' : '#8b5cf6'} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  inputArea: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    paddingBottom: Platform.OS === 'ios' ? 32 : 16,
  },
  inputContainer: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginRight: 12,
  },
  input: {
    color: '#e5e7eb',
    fontSize: 15,
    maxHeight: 100,
    fontWeight: '400',
    lineHeight: 20,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(139, 92, 246, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.3)',
  },
  sendButtonDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
});
