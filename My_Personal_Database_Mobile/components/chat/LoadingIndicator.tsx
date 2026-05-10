import React from 'react';
import { View, Text, ActivityIndicator, StyleSheet, Animated } from 'react-native';

interface LoadingIndicatorProps {
  loadingStage: string;
  routingDecision: string | null;
  dot1Anim: Animated.Value;
  dot2Anim: Animated.Value;
  dot3Anim: Animated.Value;
}

export default function LoadingIndicator({ loadingStage, routingDecision, dot1Anim, dot2Anim, dot3Anim }: LoadingIndicatorProps) {
  return (
    <View style={styles.loadingRow}>
      <View style={styles.assistantBubble}>
        <View style={styles.loadingContent}>
          <View style={styles.loadingIndicatorContainer}>
            <ActivityIndicator color="#9333ea" size="small" />
          </View>
          <View style={styles.loadingTextContainer}>
            <Text style={styles.loadingText}>{loadingStage || 'Processing...'}</Text>
            {routingDecision === 'general' && (
              <Text style={styles.loadingSubtext}>
                This is a general conversation - no database search needed
              </Text>
            )}
          </View>
          <View style={styles.loadingDots}>
            <Animated.View style={[styles.dot, { opacity: dot1Anim, transform: [{ scale: dot1Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.3] }) }] }]} />
            <Animated.View style={[styles.dot, { opacity: dot2Anim, transform: [{ scale: dot2Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.3] }) }] }]} />
            <Animated.View style={[styles.dot, { opacity: dot3Anim, transform: [{ scale: dot3Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.3] }) }] }]} />
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  assistantBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  loadingContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  loadingIndicatorContainer: {
    marginRight: 12,
  },
  loadingText: {
    color: '#cbd5e1',
    fontSize: 14,
    fontWeight: '500',
  },
  loadingTextContainer: {
    flex: 1,
  },
  loadingSubtext: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '400',
    marginTop: 4,
    fontStyle: 'italic',
  },
  loadingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#9333ea',
    marginHorizontal: 3,
  },
});
