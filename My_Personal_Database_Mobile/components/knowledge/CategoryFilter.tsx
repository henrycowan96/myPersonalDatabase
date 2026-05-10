import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';

interface CategoryFilterProps {
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
  getCategoryColor: (category: string) => string;
}

export default function CategoryFilter({ categories, selectedCategory, onSelectCategory, getCategoryColor }: CategoryFilterProps) {
  const colorScheme = useColorScheme();

  const formatCategory = (cat: string) => {
    return cat
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <ScrollView 
      horizontal 
      showsHorizontalScrollIndicator={false} 
      style={styles.categoryScroll}
      contentContainerStyle={styles.categoryContainer}
    >
      {categories.filter(cat => cat && cat !== 'unknown').map((cat) => (
        <TouchableOpacity
          key={cat}
          style={[
            styles.categoryChip,
            selectedCategory === cat && styles.categoryChipActive,
            { 
              backgroundColor: selectedCategory === cat 
                ? getCategoryColor(cat) 
                : '#1e293b',
              borderColor: getCategoryColor(cat)
            }
          ]}
          onPress={() => onSelectCategory(cat)}
        >
          <Text style={[
            styles.categoryChipText,
            { color: selectedCategory === cat ? '#fff' : '#fff' }
          ]}>
            {formatCategory(cat)}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  categoryScroll: {
    paddingHorizontal: 20,
    marginTop: 24,
    marginBottom: 40,
  },
  categoryContainer: {
    gap: 8,
  },
  categoryChip: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
    borderWidth: 1,
    height: 28,
  },
  categoryChipActive: {
    borderWidth: 0,
  },
  categoryChipText: {
    fontSize: 14,
    fontWeight: '600',
  },
});
