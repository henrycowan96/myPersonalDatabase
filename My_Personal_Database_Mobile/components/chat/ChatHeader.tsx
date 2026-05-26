import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Plus, Trash2 } from 'lucide-react-native';

interface ChatHeaderProps {
  onNewChat: () => void;
  onClearHistory: () => void;
}

export default function ChatHeader({ onNewChat, onClearHistory }: ChatHeaderProps) {
  return (
    <View style={styles.header}>
      <Text style={styles.title}>dhaki</Text>
      <View style={styles.headerActions}>
        <TouchableOpacity onPress={onNewChat} style={styles.actionButton}>
          <Plus size={18} color="#9ca3af" />
        </TouchableOpacity>
        <TouchableOpacity onPress={onClearHistory} style={styles.actionButton}>
          <Trash2 size={18} color="#9ca3af" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#e5e7eb',
    letterSpacing: -0.5,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
});
