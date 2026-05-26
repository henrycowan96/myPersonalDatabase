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
            <ActivityIndicator color="#8b5cf6" size="small" />
          </View>
          <View style={styles.loadingTextContainer}>
            <Text style={styles.loadingText}>{loadingStage || 'Thinking...'}</Text>
            {routingDecision === 'general' && (
              <Text style={styles.loadingSubtext}>
                General conversation
              </Text>
            )}
          </View>
          <View style={styles.loadingDots}>
            <Animated.View style={[styles.dot, { opacity: dot1Anim, transform: [{ scale: dot1Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.2] }) }] }]} />
            <Animated.View style={[styles.dot, { opacity: dot2Anim, transform: [{ scale: dot2Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.2] }) }] }]} />
            <Animated.View style={[styles.dot, { opacity: dot3Anim, transform: [{ scale: dot3Anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.2] }) }] }]} />
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingRow: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  assistantBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
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
    color: '#e5e7eb',
    fontSize: 15,
    fontWeight: '400',
  },
  loadingTextContainer: {
    flex: 1,
  },
  loadingSubtext: {
    color: '#9ca3af',
    fontSize: 12,
    fontWeight: '400',
    marginTop: 2,
  },
  loadingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#8b5cf6',
    marginHorizontal: 2,
  },
});
