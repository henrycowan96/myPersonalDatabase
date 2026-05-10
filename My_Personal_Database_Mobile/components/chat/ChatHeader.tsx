import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image } from 'react-native';
import { Plus, Trash2 } from 'lucide-react-native';

interface ChatHeaderProps {
  onNewChat: () => void;
  onClearHistory: () => void;
}

export default function ChatHeader({ onNewChat, onClearHistory }: ChatHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        <Image 
          source={require('../../assets/images/icon.png')} 
          style={styles.headerIcon}
        />
        <Text style={styles.title}>Chat</Text>
      </View>
      
      <View style={styles.headerActions}>
        <TouchableOpacity onPress={onNewChat} style={styles.actionButton}>
          <Plus size={20} color="#fff" />
        </TouchableOpacity>
        <TouchableOpacity onPress={onClearHistory} style={styles.actionButton}>
          <Trash2 size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 4,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerIcon: {
    width: 32,
    height: 32,
    marginRight: 12,
    borderRadius: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  headerActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1e293b',
  },
});
