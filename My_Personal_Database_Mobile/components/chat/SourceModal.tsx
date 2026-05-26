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
                >
                  <X size={20} color="#9ca3af" />
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
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalOverlayTouchable: {
    flex: 1,
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#1e293b',
    borderRadius: 16,
    width: '100%',
    maxHeight: '80%',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 10,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  modalTitle: {
    color: '#e5e7eb',
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
  },
  modalCloseButton: {
    padding: 8,
    marginLeft: 8,
  },
  modalScroll: {
    padding: 16,
    maxHeight: '100%',
  },
  modalText: {
    color: '#d1d5db',
    fontSize: 14,
    lineHeight: 22,
  },
});
