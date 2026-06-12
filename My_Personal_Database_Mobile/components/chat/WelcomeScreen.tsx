import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Image, TouchableOpacity, Animated } from 'react-native';

interface WelcomeScreenProps {
  iconSource: any;
  onSuggestionPress?: (suggestion: string) => void;
}

export default function WelcomeScreen({ iconSource, onSuggestionPress }: WelcomeScreenProps) {
  const suggestions = [
    "What did I work on last week?",
    "Summarize my notes about project X",
    "Tell me about myself.",
  ];

  const iconScale = useRef(new Animated.Value(0)).current;
  const iconFade = useRef(new Animated.Value(0)).current;
  const titleFade = useRef(new Animated.Value(0)).current;
  const subtitleFade = useRef(new Animated.Value(0)).current;
  const suggestionAnims = suggestions.map(() => useRef(new Animated.Value(0)).current);

  useEffect(() => {
    // Icon animation
    Animated.parallel([
      Animated.spring(iconScale, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
      Animated.timing(iconFade, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();

    // Title animation (delayed)
    setTimeout(() => {
      Animated.timing(titleFade, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }).start();
    }, 200);

    // Subtitle animation (delayed)
    setTimeout(() => {
      Animated.timing(subtitleFade, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }).start();
    }, 400);

    // Suggestions staggered animation
    suggestionAnims.forEach((anim, index) => {
      setTimeout(() => {
        Animated.parallel([
          Animated.timing(anim, {
            toValue: 1,
            duration: 400,
            useNativeDriver: true,
          }),
        ]).start();
      }, 600 + index * 150);
    });
  }, []);

  return (
    <View style={styles.welcomeContainer}>
      <Animated.View style={[styles.iconContainer, { transform: [{ scale: iconScale }], opacity: iconFade }]}>
        <Animated.View style={[styles.iconGlow, { opacity: iconFade }]} />
        <Image source={iconSource} style={styles.iconImage} />
      </Animated.View>
      <Animated.Text style={[styles.title, { opacity: titleFade }]}>dhaki</Animated.Text>
      <Animated.Text style={[styles.subtitle, { opacity: subtitleFade }]}>Your personal knowledge assistant</Animated.Text>
      <View style={styles.suggestionsContainer}>
        {suggestions.map((suggestion, index) => (
          <AnimatedSuggestion
            key={index}
            suggestion={suggestion}
            onPress={() => onSuggestionPress?.(suggestion)}
            anim={suggestionAnims[index]}
          />
        ))}
      </View>
    </View>
  );
}

function AnimatedSuggestion({ suggestion, onPress, anim }: { suggestion: string; onPress: () => void; anim: Animated.Value }) {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.97,
      friction: 8,
      tension: 40,
      useNativeDriver: true,
    }).start();
  };

  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      friction: 8,
      tension: 40,
      useNativeDriver: true,
    }).start();
  };

  return (
    <Animated.View style={{ opacity: anim, transform: [{ scale: scaleAnim }] }}>
      <TouchableOpacity
        style={styles.suggestion}
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={1}
      >
        <Text style={styles.suggestionText}>{suggestion}</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  welcomeContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingHorizontal: 20,
    paddingTop: 40,
  },
  iconContainer: {
    width: 120,
    height: 120,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  iconGlow: {
    position: 'absolute',
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
    filter: 'blur(20px)',
  },
  iconImage: {
    width: 80,
    height: 80,
    resizeMode: 'contain',
    borderRadius: 24,
  },
  title: {
    color: '#f8fafc',
    fontSize: 32,
    fontWeight: '700',
    letterSpacing: -1,
    marginBottom: 8,
    textShadowColor: 'rgba(139, 92, 246, 0.3)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 8,
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: 16,
    fontWeight: '400',
    marginBottom: 48,
    letterSpacing: 0.2,
  },
  suggestionsContainer: {
    width: '100%',
    maxWidth: 420,
    gap: 16,
  },
  suggestion: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 16,
    padding: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 2,
  },
  suggestionText: {
    color: '#cbd5e1',
    fontSize: 15,
    fontWeight: '400',
    lineHeight: 22,
    letterSpacing: 0.1,
  },
});
