import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image } from 'react-native';
import { Search, RefreshCw } from 'lucide-react-native';

interface KnowledgeHeaderProps {
  onRefresh: () => void;
  refreshing: boolean;
  onSearchToggle: () => void;
}

export default function KnowledgeHeader({ onRefresh, refreshing, onSearchToggle }: KnowledgeHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        <Image 
          source={require('../../assets/images/icon.png')} 
          style={styles.headerIcon}
        />
        <Text style={styles.title}>Home</Text>
      </View>
    
      <View style={styles.headerActions}>
        <TouchableOpacity
          style={[styles.refreshButton]}
          onPress={onRefresh}
          disabled={refreshing}
        >
          {refreshing ? (
            <ActivityIndicator size="small" color="#9333ea" />
          ) : (
            <RefreshCw size={20} color="#fff" />
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.searchButton]}
          onPress={onSearchToggle}
        >
          <Search size={20} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
}

import { ActivityIndicator } from 'react-native';

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
  searchButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1e293b',
  },
  refreshButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1e293b',
  },
});
