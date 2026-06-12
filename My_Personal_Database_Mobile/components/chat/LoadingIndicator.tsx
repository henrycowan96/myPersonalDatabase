import React, { useEffect, useRef } from 'react';
import { View, Text, ActivityIndicator, StyleSheet, Animated } from 'react-native';

interface LoadingIndicatorProps {
  loadingStage: string;
  routingDecision: string | null;
  dot1Anim: Animated.Value;
  dot2Anim: Animated.Value;
  dot3Anim: Animated.Value;
}

export default function LoadingIndicator({ loadingStage, routingDecision, dot1Anim, dot2Anim, dot3Anim }: LoadingIndicatorProps) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(20)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start();

    // Pulse animation for activity indicator
    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.1,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
      ])
    );
    pulseAnimation.start();

    return () => pulseAnimation.stop();
  }, []);

  return (
    <Animated.View style={[styles.loadingRow, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
      <View style={styles.assistantBubble}>
        <View style={styles.loadingContent}>
          <Animated.View style={[styles.loadingIndicatorContainer, { transform: [{ scale: pulseAnim }] }]}>
            <ActivityIndicator color="#8b5cf6" size="small" />
          </Animated.View>
          <View style={styles.loadingTextContainer}>
            <Text style={styles.loadingText}>{loadingStage || 'Thinking...'}</Text>
            {routingDecision === 'general' && (
              <Text style={styles.loadingSubtext}>
                General conversation
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
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  loadingRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  assistantBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  loadingContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 18,
  },
  loadingIndicatorContainer: {
    marginRight: 14,
  },
  loadingText: {
    color: '#f1f5f9',
    fontSize: 15,
    fontWeight: '400',
  },
  loadingTextContainer: {
    flex: 1,
  },
  loadingSubtext: {
    color: '#94a3b8',
    fontSize: 12,
    fontWeight: '400',
    marginTop: 3,
  },
  loadingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 10,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#8b5cf6',
    marginHorizontal: 2.5,
    shadowColor: '#8b5cf6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 4,
    elevation: 2,
  },
});
