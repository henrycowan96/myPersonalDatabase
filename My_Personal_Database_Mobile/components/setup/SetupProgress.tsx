import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Check } from 'lucide-react-native';

interface SetupProgressProps {
  currentStep: number;
}

export default function SetupProgress({ currentStep }: SetupProgressProps) {
  return (
    <View style={styles.progressContainer}>
      {[1, 2, 3].map((s) => (
        <View key={s} style={styles.stepWrapper}>
          <View
            style={[
              styles.stepDot,
              s === currentStep ? styles.stepDotActive : s < currentStep ? styles.stepDotCompleted : styles.stepDotPending
            ]}
          >
            {s < currentStep ? <Check size={12} color="white" /> : <Text style={styles.stepText}>{s}</Text>}
          </View>
          {s < 3 && <View style={[styles.stepLine, s < currentStep ? styles.stepLineActive : styles.stepLinePending]} />}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    paddingHorizontal: 20,
  },
  stepWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  stepDotActive: {
    backgroundColor: '#9333ea',
    shadowColor: '#9333ea',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
  },
  stepDotCompleted: {
    backgroundColor: '#10b981',
  },
  stepDotPending: {
    backgroundColor: '#1e293b',
  },
  stepText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '900',
  },
  stepLine: {
    height: 2,
    width: 60,
    marginHorizontal: -2,
  },
  stepLineActive: {
    backgroundColor: '#9333ea',
  },
  stepLinePending: {
    backgroundColor: '#1e293b',
  },
});
