# Mobile App Architecture Documentation

## Overview

The Personal Database Mobile app is a sophisticated React Native application built with Expo, designed for optimal performance, security, and user experience. The app follows modern mobile development patterns with a focus on offline-first architecture and efficient data management.

## Architecture Principles

- **Offline-First:** Core functionality available without internet connectivity
- **Performance-Optimized:** Memory-efficient with intelligent caching
- **Secure:** End-to-end encryption and secure authentication
- **Scalable:** Modular component architecture
- **User-Centric:** Intuitive UX with minimal friction

## Technology Stack

### Core Framework
- **React Native:** Cross-platform mobile development
- **Expo SDK:** Development platform and tooling
- **Expo Router:** File-based routing system
- **TypeScript:** Type-safe development

### State Management
- **React Hooks:** Local component state
- **Context API:** Global application state
- **AsyncStorage:** Persistent local storage
- **Custom Memory Manager:** Intelligent cache management

### UI/UX
- **React Native Elements:** UI component library
- **React Native Vector Icons:** Icon system
- **React Native Reanimated:** Smooth animations
- **React Native Gesture Handler:** Touch interactions

### Authentication & Security
- **Supabase Auth:** User authentication and session management
- **Expo SecureStore:** Secure credential storage
- **JWT Tokens:** Secure API authentication

### Data & Networking
- **Axios:** HTTP client with interceptors
- **React Query (TanStack Query):** Server state management
- **Custom Cache Layer:** Intelligent data caching

## Project Structure

```
My Personal Database Mobile/
├── app/                          # Application screens and routing
│   ├── (tabs)/                   # Tab navigation screens
│   │   ├── _layout.tsx          # Tab navigation container
│   │   ├── knowledge.tsx        # Knowledge/search screen
│   │   ├── chat.tsx             # Chat interface
│   │   └── settings.tsx         # User settings
│   ├── auth/                     # Authentication flows
│   │   ├── callback.tsx         # OAuth callback handler
│   │   └── login.tsx            # Login screen
│   ├── setup/                    # Onboarding flow
│   │   └── index.tsx            # Setup wizard
│   ├── _layout.tsx              # Root layout with auth
│   ├── +html.tsx                # HTML fallback
│   └── +not-found.tsx           # 404 handler
├── components/                   # Reusable UI components
│   ├── chat/                     # Chat-specific components
│   │   ├── ChatInterface.tsx    # Main chat component
│   │   ├── MessageBubble.tsx    # Message display
│   │   └── ChatInput.tsx        # Message input
│   ├── knowledge/                # Knowledge/search components
│   │   ├── SearchBar.tsx        # Search interface
│   │   ├── DocumentCard.tsx     # Document display
│   │   ├── FilterPanel.tsx      # Search filters
│   │   └── LLMThoughtModal.tsx  # AI reasoning display
│   ├── common/                   # Shared components
│   │   ├── Button.tsx           # Custom button
│   │   ├── Input.tsx            # Custom input
│   │   ├── LoadingSpinner.tsx   # Loading indicator
│   │   └── ErrorBoundary.tsx    # Error handling
│   ├── EditScreenInfo.tsx       # Screen info component
│   ├── ExternalLink.tsx         # External link handler
│   └── StyledText.tsx           # Styled text component
├── lib/                          # Core utilities and services
│   ├── supabase.ts              # Supabase client configuration
│   ├── memoryManager.ts         # Memory management system
│   ├── api.ts                   # API client configuration
│   ├── auth.ts                  # Authentication utilities
│   ├── cache.ts                 # Caching utilities
│   ├── constants.ts             # App constants
│   └── types.ts                 # TypeScript type definitions
├── hooks/                        # Custom React hooks
│   ├── useAuth.ts               # Authentication state
│   ├── useCache.ts              # Cache management
│   ├── useDebounce.ts           # Debounced values
│   ├── useNetworkStatus.ts      # Network connectivity
│   └── useColorScheme.ts        # Theme management
├── assets/                       # Static assets
│   ├── fonts/                   # Custom fonts
│   ├── images/                  # Images and icons
│   └── icons/                   # App icons
├── app.json                      # Expo configuration
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript configuration
├── babel.config.js               # Babel configuration
├── eas.json                      # Expo Application Services
└── .env                          # Environment variables
```

## Core Components Architecture

### 1. Navigation System

#### Root Layout (`app/_layout.tsx`)
```typescript
// Authentication-aware root layout
- Session management with Supabase
- Auto-logout on app backgrounding
- Setup status checking and routing
- Theme provider integration
- Memory manager initialization
```

**Key Features:**
- **Authentication State Management:** Real-time session tracking
- **Setup Flow Control:** Automatic routing to setup if needed
- **Security:** Auto-logout when app goes to background
- **Performance:** Memory management initialization

#### Tab Navigation (`app/(tabs)/_layout.tsx`)
```typescript
// Main application navigation
- Tab-based navigation structure
- Icon-based navigation indicators
- Badge notifications
- Deep linking support
```

### 2. Authentication System

#### Login Flow (`app/auth/login.tsx`)
```typescript
// Multi-provider authentication
- Google OAuth integration
- Apple Sign-In (iOS)
- Email/password authentication
- Social provider selection
```

#### Security Features
- **Secure Storage:** Credentials stored in Expo SecureStore
- **Session Management:** Automatic token refresh
- **OAuth State Handling:** Secure OAuth flow implementation
- **Background Security:** Auto-logout on app backgrounding

### 3. Knowledge/Search System

#### Search Interface (`app/(tabs)/knowledge.tsx`)
```typescript
// Advanced search functionality
- Real-time search with debouncing
- Filter-based refinement
- Result categorization
- Source attribution
```

#### Search Components
- **SearchBar:** Intelligent search input with suggestions
- **DocumentCard:** Rich document preview with metadata
- **FilterPanel:** Advanced filtering options
- **LLMThoughtModal:** AI reasoning transparency

### 4. Chat System

#### Chat Interface (`app/(tabs)/chat.tsx`)
```typescript
// Conversational AI interface
- Real-time messaging
- Context awareness
- Message history
- Typing indicators
```

#### Chat Components
- **ChatInterface:** Main chat container
- **MessageBubble:** Message display with source attribution
- **ChatInput:** Rich text input with suggestions

## State Management Architecture

### 1. Authentication State
```typescript
// Global authentication context
interface AuthContextType {
  session: Session | null;
  user: User | null;
  loading: boolean;
  signIn: (provider: AuthProvider) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}
```

### 2. Cache Management
```typescript
// Intelligent caching system
interface CacheConfig {
  maxMemoryUsage: number;      // MB
  cleanupInterval: number;     // milliseconds
  backgroundCleanupDelay: number; // milliseconds
}

// Memory manager features
- LRU eviction strategy
- Background cleanup
- Memory pressure monitoring
- Intelligent cache warming
```

### 3. Application State
```typescript
// Global app state
interface AppState {
  setupStep: number | null;
  networkStatus: 'online' | 'offline';
  theme: 'light' | 'dark' | 'system';
  notifications: Notification[];
  searchHistory: SearchQuery[];
}
```

## Performance Optimizations

### 1. Memory Management
```typescript
// Custom memory manager
class MemoryManager {
  // Features:
  - Automatic memory pressure detection
  - Intelligent cache eviction
  - Background cleanup tasks
  - Memory usage monitoring
  - Performance metrics collection
}
```

### 2. Data Loading Strategies
- **Lazy Loading:** Components load data on demand
- **Pagination:** Large datasets loaded in chunks
- **Background Sync:** Data synchronized in background
- **Offline Support:** Cached data available offline

### 3. Rendering Optimizations
- **React.memo:** Component memoization
- **useMemo:** Expensive calculations cached
- **useCallback:** Function reference stability
- **FlatList:** Optimized list rendering

## Security Implementation

### 1. Authentication Security
```typescript
// Secure authentication flow
const signIn = async (provider: AuthProvider) => {
  try {
    // OAuth flow with state parameter
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${API_URL}/auth/callback`,
      },
    });
    
    // Secure token storage
    await SecureStore.setItemAsync('auth_token', data.session?.access_token);
  } catch (error) {
    // Error handling with user feedback
  }
};
```

### 2. Data Security
- **Encryption:** Sensitive data encrypted at rest
- **Secure Storage:** Credentials in SecureStore
- **API Security:** JWT-based API authentication
- **Certificate Pinning:** SSL certificate validation

### 3. Privacy Features
- **Local Processing:** Sensitive operations performed locally
- **Data Minimization:** Only necessary data collected
- **User Control:** Granular privacy settings
- **Audit Logging:** Data access tracking

## Offline Architecture

### 1. Offline Storage Strategy
```typescript
// Offline data management
interface OfflineStore {
  // Cached search results
  searchResults: SearchResult[];
  
  // User preferences
  userSettings: UserSettings;
  
  // Authentication tokens
  authTokens: AuthTokens;
  
  // Sync queue for pending operations
  syncQueue: SyncOperation[];
}
```

### 2. Sync Strategy
- **Background Sync:** Automatic data synchronization
- **Conflict Resolution:** Intelligent conflict handling
- **Incremental Sync:** Only changed data synchronized
- **Retry Logic:** Robust error handling with retries

### 3. Offline Features
- **Search:** Cached search results available
- **Authentication:** Offline token validation
- **Settings:** Local preference storage
- **Navigation:** Full app navigation offline

## Error Handling & User Experience

### 1. Error Boundaries
```typescript
// Global error handling
class AppErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Error logging and reporting
    // User-friendly error display
    // Recovery options
  }
}
```

### 2. Network Error Handling
- **Retry Logic:** Automatic retry with exponential backoff
- **Offline Mode:** Graceful degradation when offline
- **User Feedback:** Clear error messages and status
- **Recovery Options:** Manual retry and refresh options

### 3. Loading States
- **Skeleton Screens:** Content placeholders during loading
- **Progress Indicators:** Clear loading progress
- **Pull to Refresh:** Manual refresh capability
- **Background Loading:** Non-blocking data loading

## Testing Strategy

### 1. Unit Testing
```typescript
// Component testing with React Native Testing Library
describe('SearchBar Component', () => {
  it('should handle search input', () => {
    const { getByPlaceholderText } = render(<SearchBar />);
    const input = getByPlaceholderText('Search...');
    
    fireEvent.changeText(input, 'test query');
    expect(input.props.value).toBe('test query');
  });
});
```

### Recent Testing Updates

#### ExternalLink Component Test Fixes (May 2026)

**Component Overview**: The `ExternalLink` component is a wrapper around expo-router's Link that provides platform-specific behavior for external URLs.

**Testing Challenge**: Initial tests failed because they expected `props.onPress` to be called, but the component overrides the `onPress` handler entirely.

**Component Behavior**:
```typescript
// ExternalLink component onPress logic
onPress={(e) => {
  if (Platform.OS !== 'web') {
    // Native: prevent default, open in-app browser
    e.preventDefault();
    WebBrowser.openBrowserAsync(props.href as string);
  }
  // Web: uses default Link behavior, doesn't call props.onPress
}}
```

**Test Fixes Applied**:
1. **Mock Configuration**: Updated expo-router Link mock to properly handle component's onPress override
2. **Test Expectations**: Corrected tests to verify actual component behavior rather than assumed behavior
3. **Platform Mocking**: Ensured consistent platform simulation across tests

**Key Learning**: When testing wrapper components, verify actual component behavior rather than expected prop behavior, especially when components override props for platform-specific functionality.

### 2. Integration Testing
- **API Integration:** Backend service testing
- **Authentication Flow:** End-to-end auth testing
- **Data Flow:** Complete user journey testing
- **Performance Testing:** Memory and performance testing

### 3. E2E Testing
```typescript
// Detox E2E testing
describe('Search Flow', () => {
  it('should search and display results', async () => {
    await element(by.id('search-input')).typeText('test query');
    await element(by.id('search-button')).tap();
    await expect(element(by.id('search-results'))).toBeVisible();
  });
});
```

## Deployment & Distribution

### 1. Build Configuration
```json
// app.json configuration
{
  "expo": {
    "name": "Personal Database",
    "version": "1.0.0",
    "orientation": "portrait",
    "platforms": ["ios", "android"],
    "ios": {
      "bundleIdentifier": "com.company.personaldatabase",
      "buildNumber": "1.0.0"
    },
    "android": {
      "package": "com.company.personaldatabase",
      "versionCode": 1
    }
  }
}
```

### 2. Environment Management
```typescript
// Environment-specific configuration
const config = {
  development: {
    apiUrl: 'http://localhost:8000',
    enableDebugMode: true,
    logLevel: 'debug'
  },
  production: {
    apiUrl: 'https://api.personaldatabase.com',
    enableDebugMode: false,
    logLevel: 'error'
  }
};
```

### 3. App Store Deployment
- **App Store Connect:** iOS app distribution
- **Google Play Console:** Android app distribution
- **Over-the-Air Updates:** Expo EAS updates
- **A/B Testing:** Feature rollouts and testing

## Performance Monitoring

### 1. Analytics Integration
```typescript
// Performance tracking
import { Analytics } from '@segment/analytics-react-native';

Analytics.track('Search Performed', {
  queryLength: query.length,
  resultsCount: results.length,
  responseTime: responseTime,
  userId: user.id
});
```

### 2. Crash Reporting
- **Crashlytics:** Automatic crash reporting
- **Error Logging:** Custom error tracking
- **Performance Metrics:** App performance monitoring
- **User Feedback:** In-app feedback collection

### 3. Performance Metrics
- **App Launch Time:** Cold and warm start times
- **Memory Usage:** Peak and average memory consumption
- **Network Performance:** API response times
- **User Engagement:** Feature usage analytics

## Future Enhancements

### 1. Advanced Features
- **Biometric Authentication:** Face ID/Touch ID integration
- **Voice Search:** Speech-to-text functionality
- **Push Notifications:** Real-time updates and alerts
- **Widget Support:** Home screen widgets

### 2. Platform-Specific Optimizations
- **iOS Features:** Spotlight search integration
- **Android Features:** Widget and notification channel support
- **Tablet Support:** Optimized layouts for larger screens
- **Accessibility:** Enhanced accessibility features

---

*This documentation is proprietary and confidential. All rights reserved.*
