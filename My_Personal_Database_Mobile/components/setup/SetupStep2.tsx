import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Shield, ChevronRight, LogOut } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import ProtocolSelector from './ProtocolSelector';

interface SetupStep2Props {
  selectedProtocols: Record<string, boolean>;
  onToggleProtocol: (key: string) => void;
  onBack: () => void;
  onContinue: () => void;
  onLogout: () => void;
}

export default function SetupStep2({ selectedProtocols, onToggleProtocol, onBack, onContinue, onLogout }: SetupStep2Props) {
  return (
    <View style={styles.card}>
      <View style={styles.iconContainer}>
        <LinearGradient colors={['#9333ea', '#6366f1']} style={styles.iconGradient}>
          <Shield size={48} color="white" />
        </LinearGradient>
      </View>
      <Text style={styles.cardTitle}>Connect Your Notes</Text>
      <Text style={styles.cardSubtitle}>
        Connect your Apple Notes to start chatting with them.
      </Text>
      
      <ProtocolSelector
        selectedProtocols={selectedProtocols}
        onToggleProtocol={onToggleProtocol}
      />

      <View style={styles.buttonRow}>
        <TouchableOpacity
          onPress={onBack}
          style={[styles.actionButton, styles.backButton]}
        >
          <View style={[styles.buttonGradient, styles.backButtonGradient]}>
            <Text style={styles.buttonText}>BACK</Text>
          </View>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={onContinue}
          style={[styles.actionButton, styles.continueButton]}
        >
          <LinearGradient colors={['#7c3aed', '#4f46e5']} style={styles.buttonGradient}>
            <Text style={styles.buttonText}>CONTINUE</Text>
            <ChevronRight size={20} color="white" />
          </LinearGradient>
        </TouchableOpacity>
      </View>
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
  buttonRow: {
    flexDirection: 'row',
    width: '100%',
    gap: 12,
  },
  backButton: {
    flex: 1,
  },
  continueButton: {
    flex: 2,
  },
  backButtonGradient: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
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
