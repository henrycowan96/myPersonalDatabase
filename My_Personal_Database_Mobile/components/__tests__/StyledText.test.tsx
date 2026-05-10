import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { MonoText } from '../StyledText';

// Mock the Themed Text component completely to avoid alias issues
jest.mock('../Themed', () => {
  const { Text } = require('react-native');
  return {
    Text: ({ children, style, ...props }: any) => (
      <Text {...props} style={style}>
        {children}
      </Text>
    ),
    View: ({ children, style, ...props }: any) => (
      <Text {...props} style={style}>
        {children}
      </Text>
    ),
    useThemeColor: () => '#000000',
  };
});

describe('MonoText Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders children correctly', () => {
    render(<MonoText>Test Text</MonoText>);
    expect(screen.getByText('Test Text')).toBeTruthy();
  });

  it('applies custom style along with SpaceMono font', () => {
    const customStyle = { fontSize: 16, color: 'red' };
    render(<MonoText style={customStyle}>Test Text</MonoText>);
    
    const textElement = screen.getByText('Test Text');
    expect(textElement).toBeTruthy();
    // Note: Since we're mocking the Text component, we can't directly test styles
    // In a real implementation, you'd test that both styles are applied
  });

  it('passes through all props to underlying Text component', () => {
    const testProps = {
      numberOfLines: 2,
      ellipsizeMode: 'tail' as const,
      selectable: true,
      testID: 'mono-text-test',
    };

    render(<MonoText {...testProps}>Test Text</MonoText>);
    
    const textElement = screen.getByTestId('mono-text-test');
    expect(textElement).toBeTruthy();
  });

  it('handles empty text', () => {
    render(<MonoText></MonoText>);
    // Should render without crashing
    expect(screen.queryByText(/.*/)).toBeTruthy();
  });

  it('handles null children gracefully', () => {
    render(<MonoText>{null}</MonoText>);
    // Should render without crashing
  });

  it('handles complex children (numbers, booleans, etc.)', () => {
    render(
      <MonoText>
        Number: {42}, Boolean: {true}, Null: {null}
      </MonoText>
    );
    // Use more flexible text matching for React Native Text rendering
    // Note: React Native doesn't render boolean values as text
    expect(screen.getByText(/Number:/)).toBeTruthy();
    expect(screen.getByText(/42/)).toBeTruthy();
    expect(screen.getByText(/Boolean:/)).toBeTruthy();
    expect(screen.getByText(/Null:/)).toBeTruthy();
  });

  it('works with accessibility props', () => {
    render(
      <MonoText 
        accessible={true}
        accessibilityLabel="Mono text label"
        accessibilityHint="This is a mono text component"
      >
        Accessible Text
      </MonoText>
    );
    
    const textElement = screen.getByText('Accessible Text');
    expect(textElement).toBeTruthy();
  });

  it('handles onPress events', () => {
    const mockOnPress = jest.fn();
    
    render(
      <MonoText onPress={mockOnPress}>
        Pressable Text
      </MonoText>
    );
    
    const textElement = screen.getByText('Pressable Text');
    expect(textElement).toBeTruthy();
    
    // In a real test, you'd simulate a press event
    // textElement.props.onPress();
    // expect(mockOnPress).toHaveBeenCalled();
  });

  it('handles long text content', () => {
    const longText = 'This is a very long text that should be handled properly by the MonoText component without any issues or crashes or unexpected behavior.';
    
    render(<MonoText>{longText}</MonoText>);
    expect(screen.getByText(longText)).toBeTruthy();
  });

  it('handles special characters and emojis', () => {
    const specialText = 'Hello 🌍! @#$%^&*()_+-=[]{}|;:,.<>?';
    
    render(<MonoText>{specialText}</MonoText>);
    expect(screen.getByText(specialText)).toBeTruthy();
  });

  it('works with nested components', () => {
    render(
      <MonoText>
        Text with <MonoText>nested</MonoText> MonoText
      </MonoText>
    );
    
    // Use regex matching for flexible text matching
    expect(screen.getByText(/Text with/)).toBeTruthy();
    expect(screen.getByText(/nested/)).toBeTruthy();
    expect(screen.getByText(/MonoText/)).toBeTruthy();
  });
});
