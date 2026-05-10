import React from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, Platform, KeyboardAvoidingView } from 'react-native';
import { Send } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

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
            placeholder="Input your questions here..."
            placeholderTextColor="#64748b"
            value={query}
            onChangeText={setQuery}
            multiline
            maxLength={2000}
          />
        </View>
        <TouchableOpacity
          onPress={onSend}
          disabled={loading || !query.trim()}
          style={styles.sendButton}
        >
          <LinearGradient
            colors={loading || !query.trim() ? ['#1e293b', '#0f172a'] : ['#9333ea', '#6366f1']}
            style={styles.sendGradient}
          >
            <Send size={20} color="white" />
          </LinearGradient>
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
    borderTopColor: 'rgba(99, 102, 241, 0.2)',
    paddingBottom: Platform.OS === 'ios' ? 32 : 16,
  },
  inputContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(99, 102, 241, 0.3)',
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginRight: 12,
  },
  input: {
    color: '#e2e8f0',
    fontSize: 15,
    maxHeight: 100,
    fontWeight: '500',
    lineHeight: 20,
  },
  sendButton: {
    width: 52,
    height: 52,
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#9333ea',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  sendGradient: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
