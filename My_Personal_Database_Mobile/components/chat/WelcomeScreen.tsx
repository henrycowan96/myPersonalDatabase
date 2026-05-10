import React from 'react';
import { View, Text, Image, StyleSheet, Platform } from 'react-native';

interface WelcomeScreenProps {
  iconSource: any;
}

export default function WelcomeScreen({ iconSource }: WelcomeScreenProps) {
  return (
    <View style={styles.welcomeContainer}>
      <Image 
        source={iconSource} 
        style={styles.welcomeIcon}
      />
      <Text style={styles.dhakiText}>dhaki</Text>
      <Text style={styles.welcomeText}>Understand everything.</Text>
      <Text style={styles.welcomeText}>Answer anything.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  welcomeContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 400,
    paddingVertical: 40,
  },
  welcomeIcon: {
    width: 120,
    height: 120,
    borderRadius: 24,
    marginBottom: 24,
  },
  welcomeText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 1,
    textAlign: 'center',
    marginBottom: 8,
  },
  dhakiText: {
    color: '#9333ea',
    fontSize: 36,
    fontWeight: '300',
    letterSpacing: 6,
    textAlign: 'center',
    marginBottom: 16,
    textTransform: 'lowercase',
    fontFamily: Platform.OS === 'ios' ? 'System' : 'sans-serif',
    textShadowColor: 'rgba(147, 51, 234, 0.15)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
    opacity: 0.95,
  },
});
