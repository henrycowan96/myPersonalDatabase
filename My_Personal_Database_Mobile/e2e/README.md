# Detox End-to-End Testing

This directory contains Detox end-to-end tests for the Personal Database Mobile React Native app.

## Setup

### Prerequisites

1. Install Detox CLI globally:
```bash
npm install -g detox-cli
```

2. For iOS testing, install Xcode and iOS Simulator
3. For Android testing, install Android Studio and Android Emulator

### Configuration

The Detox configuration is in `.detoxrc.js` at the root of the project.

### Test Scripts

- `npm run test:e2e` - Run all E2E tests
- `npm run test:e2e:ios` - Run tests on iOS simulator
- `npm run test:e2e:android` - Run tests on Android emulator
- `npm run test:e2e:build:ios` - Build iOS app for testing
- `npm run test:e2e:build:android` - Build Android app for testing

## Test Files

### `starter.test.js`
Main app functionality tests including:
- App launch and initialization
- Login screen
- Authentication flow
- Main app interface
- Chat functionality
- Navigation and tab bar
- Error handling
- Accessibility

### `auth.test.js`
Authentication-specific tests including:
- Login form validation
- Sign up process
- Password reset
- Social authentication
- Session persistence

### `setup.test.js`
Setup flow tests including:
- Setup screen navigation
- Step-by-step setup process
- Data source selection
- Permission handling
- Setup completion
- Progress tracking
- Error handling

## Running Tests

### iOS Tests
```bash
# Build and run iOS tests
npm run test:e2e:build:ios
npm run test:e2e:ios

# Or run in one command
detox test --configuration ios.sim.debug
```

### Android Tests
```bash
# Build and run Android tests
npm run test:e2e:build:android
npm run test:e2e:android

# Or run in one command
detox test --configuration android.emu.debug
```

### Running Specific Tests
```bash
# Run specific test file
detox test e2e/auth.test.js --configuration ios.sim.debug

# Run specific test case
detox test e2e/auth.test.js --configuration ios.sim.debug --grep "Login Screen"
```

## Test Structure

### Test Organization
- Tests are organized by feature (auth, setup, main app)
- Each test file contains multiple `describe` blocks for logical grouping
- Tests use `beforeAll` and `beforeEach` for setup and cleanup

### Element Identification
- Tests use `by.id()` for unique element identification
- Tests use `by.text()` for text-based element identification
- Tests use `by.label()` for accessibility labels

### Waits and Timeouts
- Tests use `waitFor()` for asynchronous operations
- Appropriate timeouts are set for different operations
- Loading states are properly handled

### Assertions
- Tests use `expect()` for assertions
- Visibility, text content, and existence are commonly checked
- Error states are validated

## Best Practices

### Test Design
- Tests should be independent and not rely on each other
- Each test should clean up after itself
- Tests should test user behavior, not implementation details
- Use meaningful test names that describe what is being tested

### Element IDs
- Ensure all interactive elements have test IDs
- Use consistent naming conventions for test IDs
- Add accessibility labels for better test reliability

### Mocking
- Network requests should be mocked when possible
- Authentication flows should be mocked for reliable testing
- External dependencies should be isolated

### Data Management
- Use test data that is consistent and predictable
- Clean up test data after tests complete
- Avoid using production data in tests

## Troubleshooting

### Common Issues

1. **Build Failures**: Ensure the app builds successfully outside of Detox
2. **Simulator/Emulator Issues**: Make sure the simulator/emulator is properly configured
3. **Timeout Issues**: Increase timeouts for slow operations
4. **Element Not Found**: Verify element IDs and accessibility labels

### Debugging

1. Use `detox test --configuration ios.sim.debug --inspect` for debugging
2. Check Detox logs for detailed error information
3. Use `device.launchApp({ newInstance: true })` for clean test starts
4. Use `device.reloadReactNative()` for fresh app state

### Performance

1. Use `device.launchApp({ newInstance: false })` for faster test runs
2. Share setup between tests when appropriate
3. Avoid unnecessary waits and delays

## Continuous Integration

### GitHub Actions
Configure CI to run Detox tests:
```yaml
- name: Run E2E Tests
  run: npm run test:e2e:ios
```

### Headless Testing
For CI environments, run tests without UI:
```bash
detox test --configuration ios.sim.debug --headless
```

## Maintenance

### Regular Updates
- Keep Detox updated to latest version
- Update test configurations when app changes
- Review and update tests regularly

### Test Coverage
- Aim for high coverage of user flows
- Test both happy path and error scenarios
- Include accessibility tests

## Resources

- [Detox Documentation](https://github.com/wix/Detox/blob/master/docs/README.md)
- [React Native Testing Guide](https://reactnative.dev/docs/testing-overview)
- [Expo Testing with Detox](https://docs.expo.dev/guides/testing-with-detox/)
