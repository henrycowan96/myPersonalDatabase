import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';

interface WelcomeScreenProps {
  iconSource: any;
}

export default function WelcomeScreen({ iconSource }: WelcomeScreenProps) {
  return (
    <View style={styles.welcomeContainer}>
      <View style={styles.iconContainer}>
        <Image source={iconSource} style={styles.iconImage} />
      </View>
      <Text style={styles.title}>dhaki</Text>
      <Text style={styles.subtitle}>Your personal knowledge assistant</Text>
      <View style={styles.suggestionsContainer}>
        <View style={styles.suggestion}>
          <Text style={styles.suggestionText}>"What did I work on last week?"</Text>
        </View>
        <View style={styles.suggestion}>
          <Text style={styles.suggestionText}>"Summarize my notes about project X"</Text>
        </View>
        <View style={styles.suggestion}>
          <Text style={styles.suggestionText}>"Tell me about myself."</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  welcomeContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingHorizontal: 20,
    
  },
  iconContainer: {
    width: 120,
    height: 120,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    
  },
  iconImage: {
    width: 75,
    height: 75,
    resizeMode: 'contain',
    borderRadius: 20,
  },
  title: {
    color: '#e5e7eb',
    fontSize: 28,
    fontWeight: '600',
    letterSpacing: -0.5,
    marginBottom: 8,
  },
  subtitle: {
    color: '#9ca3af',
    fontSize: 15,
    fontWeight: '400',
    marginBottom: 32,
  },
  suggestionsContainer: {
    width: '100%',
    maxWidth: 400,
    gap: 12,
  },
  suggestion: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 12,
    padding: 16,
  },
  suggestionText: {
    color: '#d1d5db',
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 20,
  },
});
