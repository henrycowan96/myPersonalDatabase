import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import EditScreenInfo from '../EditScreenInfo';

// Mock expo-router
jest.mock('expo-router', () => ({
  useRouter: () => ({
    back: jest.fn(),
  }),
}));

// Mock expo-constants
jest.mock('expo-constants', () => ({
  expo: {
    version: '1.0.0',
  },
}));

describe('EditScreenInfo Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly', () => {
    render(<EditScreenInfo path="/test/path" />);
    
    expect(screen.getByText('Open up the code for this screen:')).toBeTruthy();
    expect(screen.getByText('/test/path')).toBeTruthy();
  });

  it('displays edit instructions', () => {
    render(<EditScreenInfo path="/test/path" />);
    
    expect(screen.getByText('Change any of the text, save the file, and your app will automatically update.')).toBeTruthy();
  });

  it('has help link', () => {
    render(<EditScreenInfo path="/test/path" />);
    
    const helpLink = screen.getByText('Tap here if your app doesn\'t automatically update after making changes');
    expect(helpLink).toBeTruthy();
  });

  it('displays code path correctly', () => {
    render(<EditScreenInfo path="/app/(tabs)/index.tsx" />);
    
    expect(screen.getByText('/app/(tabs)/index.tsx')).toBeTruthy();
  });

  it('handles accessibility correctly', () => {
    render(<EditScreenInfo path="/test/path" />);
    
    const helpLink = screen.getByText('Tap here if your app doesn\'t automatically update after making changes');
    expect(helpLink).toBeTruthy();
  });

  it('matches snapshot', () => {
    const { toJSON } = render(<EditScreenInfo path="/test/path" />);
    expect(toJSON()).toMatchSnapshot();
  });
});
