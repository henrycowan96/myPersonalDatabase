# Testing Guide

This document provides comprehensive testing guidelines and setup instructions for the Personal Database Mobile project.

## Overview

The project implements a multi-layered testing strategy covering:
- **Unit Tests** - Individual function and component testing
- **Integration Tests** - API-client communication and database operations
- **Component Tests** - React Native component testing with Jest
- **Service Tests** - External service integration with mocks

## Backend Testing (Python)

### Setup

1. Install testing dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
# Run all tests with coverage
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration    # Integration tests only
pytest -m slow          # Slow tests only

# Run with coverage report
pytest --cov=app --cov-report=html
```

### Test Structure

```
app/
├── __tests__/
│   ├── conftest.py              # Shared fixtures and mocks
│   ├── test_api.py              # API endpoint tests
│   ├── test_data_processor.py   # Data processing tests
│   ├── test_integration_api_client.py    # API integration tests
│   ├── test_integration_database.py       # Database integration tests
│   └── test_integration_auth.py          # Authentication integration tests
└── services/
    └── tests/
        ├── test_google_services.py        # Google service tests
        └── test_apple_services.py        # Apple service tests
```

### Key Test Categories

#### Unit Tests (`@pytest.mark.unit`)
- Individual function testing
- Component isolation
- Mock external dependencies
- Fast execution

#### Integration Tests (`@pytest.mark.integration`)
- API-client communication
- Database operations
- Service interactions
- End-to-end workflows

### Mocking Strategy

The test suite uses comprehensive mocking:
- **Pinecone**: Vector database operations
- **Supabase**: User data and authentication
- **External APIs**: Google, Apple services
- **Embedding Models**: Sentence transformers

## Frontend Testing (React Native)

### Setup

1. Install dependencies:
```bash
cd "My Personal Database Mobile"
npm install
```

2. Run tests:
```bash
# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage

# CI mode (no watch, full coverage)
npm run test:ci
```

### Test Structure

```
components/
├── __tests__/
│   ├── StyledText.test.tsx      # Component tests
│   └── ExternalLink.test.tsx    # Component tests
├── Themed.tsx                 # Theme components
└── test-setup.js              # Jest configuration
```

### Component Testing Features

- **Rendering Tests**: Verify components render correctly
- **Props Testing**: Test component prop handling
- **Event Testing**: User interaction simulation
- **Accessibility Testing**: ARIA props and screen reader support
- **Platform Testing**: iOS/Android/Web behavior

## Configuration Files

### Backend (pytest.ini)
```ini
[tool:pytest]
testpaths = app
python_files = test_*.py
addopts = -v --tb=short --cov=app --cov-report=term-missing
markers = unit, integration, slow, external
```

### Frontend (jest.config.js)
```javascript
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterEnv: ['<rootDir>/test-setup.js'],
  testMatch: ['**/__tests__/**/*.(js|jsx|ts|tsx)'],
  collectCoverageFrom: ['components/**/*.{js,jsx,ts,tsx}'],
  coverageThreshold: { global: { branches: 70, functions: 70, lines: 70, statements: 70 } }
};
```

## Running Tests

### Development Workflow

1. **Before committing**:
   ```bash
   # Backend
   pytest -m unit
   
   # Frontend
   npm test
   ```

2. **Full test suite**:
   ```bash
   # Backend with coverage
   pytest --cov=app --cov-report=html
   
   # Frontend with coverage
   npm run test:coverage
   ```

3. **CI/CD Pipeline**:
   ```bash
   # Backend
   npm run test:ci
   
   # Frontend
   npm run test:ci
   ```

### Test Categories by Priority

#### High Priority (Always Run)
- Unit tests for core functions
- Component rendering tests
- API endpoint tests
- Basic integration tests

#### Medium Priority (Run on PR)
- Service integration tests
- Database operation tests
- Authentication flow tests
- Complex component interactions

#### Low Priority (Run Nightly)
- Performance tests
- Load tests
- End-to-end tests
- Cross-platform compatibility

## Best Practices

### Writing Tests

1. **Descriptive Names**: Use clear, descriptive test names
2. **AAA Pattern**: Arrange, Act, Assert
3. **Single Responsibility**: One assertion per test when possible
4. **Mock External Dependencies**: Never call real external services
5. **Test Edge Cases**: Empty data, null values, error conditions

### Test Data Management

1. **Fixtures**: Use pytest fixtures for reusable test data
2. **Factories**: Use factory patterns for complex objects
3. **Cleanup**: Ensure tests clean up after themselves
4. **Isolation**: Tests should not depend on each other

### Coverage Goals

- **Backend**: 80%+ line coverage
- **Frontend**: 70%+ line coverage
- **Critical Paths**: 100% coverage for authentication and data processing

## Recent Fixes & Updates

### ExternalLink Component Test Fixes (May 2026)

**Issue**: Tests in `ExternalLink.test.tsx` were failing because they expected `props.onPress` to be called, but the component overrides the `onPress` handler and never calls the original prop.

**Root Cause**: 
- The `ExternalLink` component defines its own `onPress` handler that handles platform-specific behavior
- On web platforms, it uses default Link behavior
- On native platforms, it prevents default and opens an in-app browser via `WebBrowser.openBrowserAsync()`
- The original `props.onPress` is never actually called by the component

**Fixes Applied**:
1. **Updated expo-router Link mock**: Fixed the mock to properly handle the `onPress` prop passed from the ExternalLink component
2. **Corrected test expectations**: Updated tests to match actual component behavior instead of expecting incorrect `onPress` calls
3. **Fixed platform mocking**: Ensured consistent platform mocking for reliable test results

**Tests Fixed**:
- `handles onPress on web platform` - Now verifies component renders and can be pressed without error
- `handles onPress event correctly` - Updated to match actual component behavior

**Result**: All 28 tests now pass (3 test suites, 1 snapshot)

## Troubleshooting

### Common Issues

1. **Import Errors**: Check PYTHONPATH and sys.path setup
2. **Mock Failures**: Verify mock configuration in conftest.py
3. **Async Tests**: Use pytest-asyncio for async functions
4. **Database Tests**: Ensure proper cleanup between tests
5. **Component Test Failures**: Verify test expectations match actual component behavior, not assumed behavior

### Debugging Tests

```bash
# Run with verbose output
pytest -v -s

# Stop on first failure
pytest -x

# Run specific test
pytest app/__tests__/test_api.py::TestAPIEndpoints::test_root_endpoint

# Debug with pdb
pytest --pdb
```

## Continuous Integration

### GitHub Actions (Recommended)

```yaml
name: Tests
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd "My Personal Database Mobile" && npm install
      - name: Run tests
        run: cd "My Personal Database Mobile" && npm run test:ci
```

## Performance Testing

### Load Testing

```bash
# Backend load testing
pytest -m slow --benchmark-only

# Frontend performance
npm run test:performance
```

### Memory Testing

```bash
# Python memory profiling
pytest --memprof

# React Native memory testing
npm run test:memory
```

## Security Testing

### Security Test Coverage

- **Input Validation**: SQL injection, XSS prevention
- **Authentication**: Token handling, session management
- **Authorization**: Access control testing
- **Data Encryption**: Sensitive data protection

### Running Security Tests

```bash
# Backend security tests
pytest -m security

# Frontend security tests
npm run test:security
```

## Documentation

### Test Documentation

- **README.md**: Quick start guide
- **TESTING.md**: Comprehensive testing guide (this file)
- **Code Comments**: Inline test documentation
- **Coverage Reports**: HTML coverage in `htmlcov/` and `coverage/`

### API Documentation

- **OpenAPI/Swagger**: Auto-generated API docs
- **Postman Collections**: API testing collections
- **Component Storybook**: UI component documentation

## Future Enhancements

### Planned Improvements

1. **Visual Regression Testing**: Percy, Chromatic
2. **E2E Testing**: Detox, Cypress
3. **Performance Monitoring**: Lighthouse CI
4. **Accessibility Testing**: axe-core integration
5. **Contract Testing**: Pact for API contracts

### Testing Tools Roadmap

- **Backend**: Add property-based testing with Hypothesis
- **Frontend**: Add visual testing with Storybook
- **Integration**: Add contract testing with Pact
- **Performance**: Add benchmarking with pytest-benchmark
