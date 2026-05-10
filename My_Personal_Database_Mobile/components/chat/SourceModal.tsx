import React from 'react';
import { View, Text, ScrollView, Modal, TouchableOpacity, StyleSheet } from 'react-native';

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
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>
              {source ? getSourceTitle(source) : ''}
            </Text>
            <TouchableOpacity
              onPress={onClose}
              style={styles.modalCloseButton}
            >
              <Text style={styles.modalCloseText}>×</Text>
            </TouchableOpacity>
          </View>
          <ScrollView style={styles.modalScroll} showsVerticalScrollIndicator={false}>
            <Text style={styles.modalText}>
              {source?.content || 'Content not available'}
            </Text>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: '#1e293b',
    borderRadius: 20,
    width: '100%',
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 12,
    elevation: 10,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  modalTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
    flex: 1,
  },
  modalCloseButton: {
    padding: 8,
    marginLeft: 12,
  },
  modalCloseText: {
    color: '#9333ea',
    fontSize: 32,
    fontWeight: '300',
    lineHeight: 32,
  },
  modalScroll: {
    padding: 20,
    maxHeight: '100%',
  },
  modalText: {
    color: '#cbd5e1',
    fontSize: 14,
    lineHeight: 22,
  },
});
