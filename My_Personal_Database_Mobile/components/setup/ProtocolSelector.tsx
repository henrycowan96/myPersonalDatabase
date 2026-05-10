import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { Check } from 'lucide-react-native';

interface ProtocolSelectorProps {
  selectedProtocols: Record<string, boolean>;
  onToggleProtocol: (key: string) => void;
  readonly?: boolean;
}

export default function ProtocolSelector({ selectedProtocols, onToggleProtocol, readonly = false }: ProtocolSelectorProps) {
  const protocols = [
    { key: 'appleNotes', name: 'Apple Notes', icon: '📝' },
    { key: 'appleCalendar', name: 'Apple Calendar', icon: '📅' },
    { key: 'appleMusic', name: 'Apple Music', icon: '🎵' },
    ...(Platform.OS === 'ios' ? [{ key: 'iosContacts', name: 'iOS Contacts', icon: '👤' }] : []),
    ...(Platform.OS === 'android' ? [{ key: 'androidContacts', name: 'Android Contacts', icon: '📱' }] : []),
    { key: 'locationData', name: 'Location Data', icon: '📍' },
    { key: 'spotify', name: 'Spotify', icon: '🎧' },
    { key: 'googleCalendar', name: 'Google Calendar', icon: '📆' },
    { key: 'gmail', name: 'Gmail Archive', icon: '📧' },
    { key: 'googleDrive', name: 'Google Drive', icon: '💾' },
    { key: 'github', name: 'GitHub', icon: '🐙' },
    { key: 'zoom', name: 'Zoom', icon: '📹' },
  ];

  return (
    <View style={styles.protocolsList}>
      <Text style={styles.protocolsTitle}>{readonly ? 'SELECTED PROTOCOLS:' : 'SELECT PROTOCOLS:'}</Text>
      {protocols
        .filter(protocol => readonly ? selectedProtocols[protocol.key] : true)
        .map((protocol) => (
          <TouchableOpacity
            key={protocol.key}
            onPress={() => !readonly && onToggleProtocol(protocol.key)}
            disabled={readonly}
            style={[
              styles.protocolItem,
              readonly ? styles.protocolItemFinal : (
                selectedProtocols[protocol.key] ? styles.protocolItemSelected : styles.protocolItemDeselected
              )
            ]}
          >
            <Text style={styles.protocolIcon}>{protocol.icon}</Text>
            <Text style={[
              styles.protocolName,
              readonly ? styles.protocolNameFinal : (
                selectedProtocols[protocol.key] ? styles.protocolNameSelected : styles.protocolNameDeselected
              )
            ]}>
              {protocol.name}
            </Text>
            {readonly ? (
              <Check size={16} color="#10b981" />
            ) : selectedProtocols[protocol.key] ? (
              <Check size={16} color="#10b981" />
            ) : (
              <View style={styles.deselectedIndicator} />
            )}
          </TouchableOpacity>
        ))}
      {Object.values(selectedProtocols).filter(v => v).length === 0 && (
        <Text style={styles.noProtocolsText}>No protocols selected</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  protocolsList: {
    width: '100%',
    marginBottom: 32,
  },
  protocolsTitle: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 2,
    marginBottom: 16,
  },
  protocolItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
  },
  protocolItemSelected: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  protocolItemDeselected: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  protocolItemFinal: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  protocolIcon: {
    fontSize: 18,
    marginRight: 12,
  },
  protocolName: {
    flex: 1,
    fontSize: 14,
    fontWeight: '600',
  },
  protocolNameSelected: {
    color: '#e2e8f0',
  },
  protocolNameDeselected: {
    color: '#64748b',
  },
  protocolNameFinal: {
    color: '#e2e8f0',
  },
  deselectedIndicator: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#475569',
  },
  noProtocolsText: {
    color: '#64748b',
    fontSize: 14,
    textAlign: 'center',
    paddingVertical: 20,
  },
});
