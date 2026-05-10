import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { X, FileText } from 'lucide-react-native';

interface DocumentInfo {
  id: string;
  title?: string;
  source: string;
  type: string;
  content?: string;
  snippet?: string;
  metadata: Record<string, any>;
  relevance_score?: number;
}

interface DocumentModalProps {
  document: DocumentInfo;
  onClose: () => void;
}

export default function DocumentModal({ document, onClose }: DocumentModalProps) {
  return (
    <View style={styles.detailContainer}>
      <View style={styles.detailHeader}>
        <View style={styles.detailIconContainer}>
          <FileText size={24} color="#9333ea" />
        </View>
        <Text style={[
          styles.detailTitle,
          { color: '#fff' }
        ]}>
          Source Document
        </Text>
        <TouchableOpacity
          style={styles.closeButtonContainer}
          onPress={onClose}
        >
          <X size={24} color="#9333ea" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Text style={[
          styles.detailType,
          { color: '#ffffffcc' }
        ]}>
          {document.metadata?.source || 'Unknown'}
        </Text>

        <View style={styles.documentContent}>
          <Text style={[
            styles.documentFullText,
            { color: '#fff' }
          ]}>
            {document.metadata?.text || 'Content not available'}
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  detailContainer: {
    position: 'absolute',
    top: 100,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
    padding: 20,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: 'rgba(147, 51, 234, 0.3)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 10,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  detailHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  detailIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  detailTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    flex: 1,
  },
  closeButtonContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailType: {
    fontSize: 16,
    marginBottom: 16,
  },
  scrollContent: {
    flex: 1,
    marginTop: 8,
  },
  documentContent: {
    marginVertical: 16,
  },
  documentFullText: {
    fontSize: 14,
    lineHeight: 20,
  },
});
