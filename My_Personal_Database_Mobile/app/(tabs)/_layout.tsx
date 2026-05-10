import React from 'react';
import { Tabs } from 'expo-router';
import { MessageSquare, Settings, Clock, Brain, ArrowRightLeft } from 'lucide-react-native';
import { useColorScheme } from '@/components/useColorScheme';
import Colors from '@/constants/Colors';

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      initialRouteName="knowledge"
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'dark'].tint,
        tabBarInactiveTintColor: Colors[colorScheme ?? 'dark'].tabIconDefault,
        tabBarStyle: {
          backgroundColor: Colors[colorScheme ?? 'dark'].tabBarBackground,
          borderTopColor: Colors[colorScheme ?? 'dark'].tabBarBorder,
          borderTopWidth: 1,
          height: 70,
          paddingBottom: 4,
          paddingTop: 4,
        },
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '600',
          letterSpacing: 0.5,
        },
        headerShown: false,
      }}>
      <Tabs.Screen
        name="knowledge"
        options={{
          title: 'Knowledge',
          tabBarIcon: ({ color, focused }) => <Brain size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="timeline"
        options={{
          title: 'Timeline',
          tabBarIcon: ({ color, focused }) => <ArrowRightLeft size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="index"
        options={{
          title: 'Chat',
          tabBarIcon: ({ color, focused }) => <MessageSquare size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="sessions"
        options={{
          title: 'Sessions',
          tabBarIcon: ({ color, focused }) => <Clock size={24} color={color} />,
        }}
      />
      <Tabs.Screen
        name="two"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color, focused }) => <Settings size={24} color={color} />,
        }}
      />
    </Tabs>
  );
}
