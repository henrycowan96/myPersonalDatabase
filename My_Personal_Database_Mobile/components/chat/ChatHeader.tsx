import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Plus, Trash2 } from 'lucide-react-native';

interface ChatHeaderProps {
  onNewChat: () => void;
  onClearHistory: () => void;
  hasData?: boolean;
}

export default function ChatHeader({ onNewChat, onClearHistory, hasData = true }: ChatHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.titleContainer}>
        <Text style={styles.title}>dhaki</Text>
        <View style={styles.titleDot} />
      </View>
      {!hasData && (
        <TouchableOpacity style={styles.warningBadge} onPress={() => {}}>
          <Text style={styles.warningText}>connect data in settings</Text>
        </TouchableOpacity>
      )}
      <View style={styles.headerActions}>
        <TouchableOpacity onPress={onNewChat} style={styles.actionButton} activeOpacity={0.7}>
          <Plus size={18} color="#94a3b8" />
        </TouchableOpacity>
        <TouchableOpacity onPress={onClearHistory} style={styles.actionButton} activeOpacity={0.7}>
          <Trash2 size={18} color="#94a3b8" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  titleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#f8fafc',
    letterSpacing: -0.8,
  },
  titleDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#8b5cf6',
    shadowColor: '#8b5cf6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 6,
    elevation: 4,
  },
  warningBadge: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
  },
  warningText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 10,
  },
  actionButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
});
