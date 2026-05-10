import * as React from 'react';
import renderer from 'react-test-renderer';

import { MonoText } from '../StyledText';

// Mock Themed Text component completely to avoid alias issues
jest.mock('../Themed', () => {
  const { Text } = require('react-native');
  return {
    Text: ({ children, style, ...props }) => (
      <Text {...props} style={style}>
        {children}
      </Text>
    ),
    View: ({ children, style, ...props }) => (
      <Text {...props} style={style}>
        {children}
      </Text>
    ),
    useThemeColor: () => '#000000',
  };
});

it(`renders correctly`, () => {
  const tree = renderer.create(<MonoText>Snapshot test!</MonoText>).toJSON();

  expect(tree).toMatchSnapshot();
});
