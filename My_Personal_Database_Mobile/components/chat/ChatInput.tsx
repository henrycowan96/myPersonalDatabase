import React, { useEffect, useRef } from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet, Platform, KeyboardAvoidingView, Animated } from 'react-native';
import { Send } from 'lucide-react-native';

interface ChatInputProps {
  query: string;
  setQuery: (text: string) => void;
  loading: boolean;
  onSend: () => void;
}

export default function ChatInput({ query, setQuery, loading, onSend }: ChatInputProps) {
  const slideAnim = useRef(new Animated.Value(100)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const sendButtonScale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const handleSendPress = () => {
    Animated.sequence([
      Animated.timing(sendButtonScale, {
        toValue: 0.9,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(sendButtonScale, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();
    onSend();
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
    >
      <Animated.View style={[styles.inputArea, { transform: [{ translateY: slideAnim }], opacity: fadeAnim }]}>
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.input}
            placeholder="Message dhaki..."
            placeholderTextColor="#64748b"
            value={query}
            onChangeText={setQuery}
            multiline
            maxLength={2000}
            textAlignVertical="top"
          />
        </View>
        <Animated.View style={{ transform: [{ scale: sendButtonScale }] }}>
          <TouchableOpacity
            onPress={handleSendPress}
            disabled={loading || !query.trim()}
            style={[
              styles.sendButton,
              (loading || !query.trim()) && styles.sendButtonDisabled
            ]}
            activeOpacity={0.7}
          >
            <Send size={18} color={loading || !query.trim() ? '#64748b' : '#8b5cf6'} strokeWidth={2} />
          </TouchableOpacity>
        </Animated.View>
      </Animated.View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  inputArea: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
    paddingBottom: Platform.OS === 'ios' ? 32 : 16,
  },
  inputContainer: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 18,
    paddingVertical: 14,
    marginRight: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  input: {
    color: '#f1f5f9',
    fontSize: 16,
    maxHeight: 100,
    fontWeight: '400',
    lineHeight: 22,
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(139, 92, 246, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.4)',
    shadowColor: '#8b5cf6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  sendButtonDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderColor: 'rgba(255, 255, 255, 0.08)',
    shadowColor: 'transparent',
    shadowOpacity: 0,
    elevation: 0,
  },
});
