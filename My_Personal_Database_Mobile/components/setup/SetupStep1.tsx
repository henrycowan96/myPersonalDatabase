import React from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator, StyleSheet } from 'react-native';
import { Database, ChevronRight, LogOut } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface SetupStep1Props {
  isProcessing: boolean;
  onCreateDatabase: () => void;
  onLogout: () => void;
}

export default function SetupStep1({ isProcessing, onCreateDatabase, onLogout }: SetupStep1Props) {
  return (
    <View style={styles.card}>
      <View style={styles.iconContainer}>
        <LinearGradient colors={['#9333ea', '#6366f1']} style={styles.iconGradient}>
          <Database size={48} color="white" />
        </LinearGradient>
      </View>
      <Text style={styles.cardTitle}>ALLOCATE STORAGE</Text>
      <Text style={styles.cardSubtitle}>
        Provision a private, encrypted vector database instance to manage your personal intelligence.
      </Text>
      <TouchableOpacity
        onPress={onCreateDatabase}
        disabled={isProcessing}
        style={styles.actionButton}
      >
        <LinearGradient colors={['#7c3aed', '#4f46e5']} style={styles.buttonGradient}>
          {isProcessing ? <ActivityIndicator color="white" /> : (
            <>
              <Text style={styles.buttonText}>CREATE DATABASE</Text>
              <ChevronRight size={20} color="white" />
            </>
          )}
        </LinearGradient>
      </TouchableOpacity>
      <TouchableOpacity
        onPress={onLogout}
        style={styles.logoutButton}
      >
        <LogOut size={16} color="#64748b" />
        <Text style={styles.logoutButtonText}>LOG OUT</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 40,
    padding: 32,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.5,
    shadowRadius: 30,
  },
  iconContainer: {
    marginBottom: 24,
    shadowColor: '#9333ea',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.4,
    shadowRadius: 20,
  },
  iconGradient: {
    width: 90,
    height: 90,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  cardTitle: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 16,
    textAlign: 'center',
  },
  cardSubtitle: {
    color: '#94a3b8',
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
    fontWeight: '500',
  },
  actionButton: {
    width: '100%',
    shadowColor: '#6366f1',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
  },
  buttonGradient: {
    height: 64,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 1,
    marginRight: 8,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(100, 116, 139, 0.3)',
  },
  logoutButtonText: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1,
    marginLeft: 8,
  },
});
