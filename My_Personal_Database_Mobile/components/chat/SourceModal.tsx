import React from 'react';
import { View, Text, ScrollView, Modal, TouchableOpacity, StyleSheet } from 'react-native';
import { X } from 'lucide-react-native';

interface Source {
  content: string;
  metadata: any;
}

interface SourceModalProps {
  visible: boolean;
  source: Source | null;
  getSourceTitle: (source: Source) => string;
  onClose: () => void;
}

export default function SourceModal({ visible, source, getSourceTitle, onClose }: SourceModalProps) {
  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <TouchableOpacity 
          style={styles.modalOverlayTouchable} 
          activeOpacity={1}
          onPress={onClose}
        >
          <View style={styles.modalContent}>
            <TouchableOpacity activeOpacity={1}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>
                  {source ? getSourceTitle(source) : ''}
                </Text>
                <TouchableOpacity
                  onPress={onClose}
                  style={styles.modalCloseButton}
                  activeOpacity={0.7}
                >
                  <X size={20} color="#94a3b8" strokeWidth={2} />
                </TouchableOpacity>
              </View>
              <ScrollView style={styles.modalScroll} showsVerticalScrollIndicator={false}>
                <Text style={styles.modalText}>
                  {source?.content || 'Content not available'}
                </Text>
              </ScrollView>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalOverlayTouchable: {
    flex: 1,
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#1e293b',
    borderRadius: 20,
    width: '100%',
    maxHeight: '85%',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 24,
    elevation: 12,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
    backgroundColor: 'rgba(30, 41, 59, 0.95)',
  },
  modalTitle: {
    color: '#f8fafc',
    fontSize: 17,
    fontWeight: '600',
    flex: 1,
    letterSpacing: -0.3,
  },
  modalCloseButton: {
    padding: 10,
    marginLeft: 8,
    borderRadius: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
  },
  modalScroll: {
    padding: 20,
    maxHeight: '100%',
  },
  modalText: {
    color: '#e2e8f0',
    fontSize: 15,
    lineHeight: 24,
    fontWeight: '400',
  },
});
