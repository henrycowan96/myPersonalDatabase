# Developer Onboarding Guide

## Overview

Welcome to the Personal Database Mobile development team! This guide will help you get up to speed with our codebase, development practices, and workflows. Whether you're working on the backend API, mobile app, or data pipeline, this document provides everything you need to start contributing effectively.

## Development Philosophy

### Core Principles
- **Privacy-First:** User data security and privacy are paramount
- **Performance-Optimized:** Every component should be efficient and scalable
- **Developer Experience:** Clean, well-documented code with excellent tooling
- **User-Centric:** Features should solve real user problems
- **Test-Driven:** Comprehensive testing at all levels

### Code Standards
- **Python:** Follow PEP 8, use type hints, write docstrings
- **TypeScript:** Strict mode enabled, prefer explicit types
- **Git:** Conventional commits, meaningful PR descriptions
- **Documentation:** Code should be self-documenting with additional context

## Getting Started

### Prerequisites Checklist

Before you begin, ensure you have:

```bash
# Required Software
- Python 3.14+
- Node.js 18+
- npm or yarn
- Git
- Docker (optional but recommended)
- VS Code (recommended) or your preferred IDE

# Platform-Specific
- macOS 13+ (for Apple ecosystem development)
- Xcode 15+ (for iOS development)
- Android Studio (for Android development)
```

### Environment Setup

#### 1. Repository Setup
```bash
# Clone the repository
git clone https://github.com/company/personal-database-mobile.git
cd personal-database-mobile

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Configure git user (if not already done)
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"
```

#### 2. Backend Development Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Copy environment template
cp .env.example .env
# Edit .env with your local configuration
```

#### 3. Mobile Development Environment
```bash
# Navigate to mobile app
cd "My Personal Database Mobile"

# Install dependencies
npm install

# Install Expo CLI globally
npm install -g @expo/cli

# Login to Expo
expo login

# Copy environment template
cp .env.example .env.local
# Edit .env.local with your local configuration
```

#### 4. Database Setup
```bash
# Start PostgreSQL (using Docker or local installation)
docker run --name postgres-db -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# Start Redis (using Docker)
docker run --name redis-cache -p 6379:6379 -d redis:7-alpine

# Run database migrations
python -m alembic upgrade head

# Create superuser account
python scripts/create_superuser.py
```

### IDE Configuration

#### VS Code Extensions (Recommended)
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "ms-vscode.vscode-eslint",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode-remote.remote-containers"
  ]
}
```

#### VS Code Settings
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "typescript.preferences.importModuleSpecifier": "relative"
}
```

## Development Workflow

### 1. Branch Strategy

We use a simplified Git flow:

```
main                    # Production-ready code
├── develop             # Integration branch
├── feature/*           # Feature branches
├── bugfix/*            # Bug fix branches
└── hotfix/*            # Critical fixes
```

#### Branch Naming Conventions
```bash
feature/user-authentication
bugfix/search-performance-issue
hotfix/security-vulnerability
```

### 2. Commit Message Format

We follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples
```bash
feat(auth): add OAuth2 integration for Google
fix(search): resolve memory leak in vector search
docs(api): update authentication endpoints documentation
refactor(database): optimize query performance
```

### 3. Development Process

#### Daily Workflow
```bash
# 1. Sync with main branch
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and commit regularly
git add .
git commit -m "feat(component): implement new feature"

# 4. Push and create PR
git push origin feature/your-feature-name
# Create pull request on GitHub/GitLab

# 5. After review and merge
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

#### Pull Request Process
1. **Create PR** from feature branch to `main`
2. **Fill PR template** with detailed description
3. **Request reviews** from team members
4. **Address feedback** and update PR
5. **Ensure CI/CD passes** all checks
6. **Merge** after approval

## Code Architecture Deep Dive

### Backend Architecture

#### Project Structure
```
app/
├── api.py                 # FastAPI application entry point
├── routes/                # API endpoint definitions
│   ├── auth.py           # Authentication endpoints
│   ├── query.py          # Search and query endpoints
│   ├── chat.py           # Chat and LLM endpoints
│   └── ...
├── services/             # Business logic layer
│   ├── auth_service.py   # Authentication business logic
│   ├── search_service.py # Search business logic
│   └── ...
├── models/               # Data models and schemas
│   ├── user.py          # User-related models
│   ├── document.py      # Document models
│   └── ...
├── utils/                # Utility functions
├── processors/           # Data processing logic
└── tests/               # Test files
```

#### Key Patterns
- **Dependency Injection:** Use FastAPI's dependency system
- **Service Layer:** Business logic separated from API layer
- **Repository Pattern:** Data access abstraction
- **Error Handling:** Custom exception classes and handlers

### Mobile Architecture

#### Project Structure
```
My Personal Database Mobile/
├── app/                  # Screens and navigation
│   ├── (tabs)/         # Tab-based screens
│   ├── auth/           # Authentication screens
│   └── setup/          # Onboarding screens
├── components/          # Reusable UI components
│   ├── common/         # Generic components
│   ├── chat/           # Chat-specific components
│   └── knowledge/      # Search components
├── lib/                # Core utilities and services
├── hooks/              # Custom React hooks
├── assets/             # Static assets
└── tests/              # Test files
```

#### Key Patterns
- **Component Composition:** Reusable, composable components
- **Custom Hooks:** Logic extraction and reuse
- **Context API:** Global state management
- **TypeScript:** Type safety throughout

## Testing Strategy

### Backend Testing

#### Test Structure
```
app/tests/
├── unit/               # Unit tests
│   ├── test_auth_service.py
│   ├── test_search_service.py
│   └── ...
├── integration/        # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── ...
└── e2e/               # End-to-end tests
    └── test_user_journey.py
```

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/unit/test_auth_service.py

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

#### Writing Tests
```python
# Example unit test
import pytest
from app.services.auth_service import AuthService

class TestAuthService:
    def setup_method(self):
        self.auth_service = AuthService()
    
    def test_create_user_success(self):
        user_data = {
            "email": "test@example.com",
            "password": "securepassword"
        }
        
        user = self.auth_service.create_user(user_data)
        
        assert user.email == user_data["email"]
        assert user.id is not None
        assert user.created_at is not None
    
    def test_create_user_duplicate_email(self):
        user_data = {
            "email": "test@example.com",
            "password": "securepassword"
        }
        
        # Create first user
        self.auth_service.create_user(user_data)
        
        # Attempt to create duplicate
        with pytest.raises(UserAlreadyExistsError):
            self.auth_service.create_user(user_data)
```

### Mobile Testing

#### Test Structure
```
My Personal Database Mobile/
├── __tests__/          # Test files
│   ├── components/     # Component tests
│   ├── screens/        # Screen tests
│   ├── hooks/          # Hook tests
│   └── utils/          # Utility tests
└── e2e/               # E2E tests (Detox)
```

#### Running Tests
```bash
# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- SearchBar.test.tsx

# Run E2E tests
npm run test:e2e
```

#### Writing Tests
```typescript
// Example component test
import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react-native';
import { SearchBar } from '../components/knowledge/SearchBar';

describe('SearchBar', () => {
  it('should handle text input', () => {
    const onSearch = jest.fn();
    
    render(<SearchBar onSearch={onSearch} />);
    
    const searchInput = screen.getByPlaceholderText('Search...');
    fireEvent.changeText(searchInput, 'test query');
    
    expect(searchInput.props.value).toBe('test query');
  });
  
  it('should call onSearch when search button is pressed', () => {
    const onSearch = jest.fn();
    
    render(<SearchBar onSearch={onSearch} />);
    
    const searchButton = screen.getByTestId('search-button');
    fireEvent.press(searchButton);
    
    expect(onSearch).toHaveBeenCalledWith('test query');
  });
});
```

## Common Development Tasks

### 1. Adding a New API Endpoint

#### Backend Steps
```python
# 1. Define the model (app/models/new_feature.py)
from pydantic import BaseModel
from typing import Optional

class NewFeatureRequest(BaseModel):
    name: str
    description: Optional[str] = None

class NewFeatureResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

# 2. Implement the service (app/services/new_feature_service.py)
class NewFeatureService:
    def create_feature(self, request: NewFeatureRequest) -> NewFeatureResponse:
        # Business logic here
        pass

# 3. Create the endpoint (app/routes/new_feature.py)
from fastapi import APIRouter, Depends
from app.services.new_feature_service import NewFeatureService

router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.post("/", response_model=NewFeatureResponse)
async def create_new_feature(
    request: NewFeatureRequest,
    service: NewFeatureService = Depends()
):
    return service.create_feature(request)

# 4. Register the router (app/api.py)
from app.routes import new_feature
app.include_router(new_feature.router)
```

#### Testing Steps
```python
# app/tests/unit/test_new_feature_service.py
class TestNewFeatureService:
    def test_create_feature_success(self):
        service = NewFeatureService()
        request = NewFeatureRequest(name="Test Feature")
        
        result = service.create_feature(request)
        
        assert result.name == request.name
        assert result.id is not None

# app/tests/integration/test_new_feature_api.py
class TestNewFeatureAPI:
    def test_create_feature_endpoint(self, client):
        request_data = {"name": "Test Feature"}
        
        response = client.post("/api/v1/new-feature/", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Feature"
```

### 2. Adding a New Mobile Screen

#### Steps
```typescript
// 1. Create the screen component (app/(tabs)/new-screen.tsx)
import React from 'react';
import { View, Text } from 'react-native';

export default function NewScreen() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>New Screen</Text>
    </View>
  );
}

// 2. Add to tab navigation (app/(tabs)/_layout.tsx)
import NewScreen from './new-screen';

<Tabs.Screen 
  name="new-screen" 
  options={{ 
    title: 'New Screen',
    tabBarIcon: ({ color, size }) => (
      <Ionicons name="new-icon" size={size} color={color} />
    )
  }} 
/>

// 3. Add navigation (if needed)
import { router } from 'expo-router';

// Navigate to screen
router.push('/(tabs)/new-screen');
```

### 3. Database Schema Changes

#### Steps
```bash
# 1. Create migration
alembic revision --autogenerate -m "Add new table"

# 2. Review and modify migration file
# alembic/versions/xxx_add_new_table.py

# 3. Apply migration
alembic upgrade head

# 4. Update models (app/models/new_model.py)
# 5. Update services to use new model
```

## Debugging Guide

### Backend Debugging

#### Common Issues
```python
# 1. Import errors
# Check: __init__.py files, PYTHONPATH, virtual environment

# 2. Database connection issues
# Check: DATABASE_URL, network connectivity, credentials

# 3. External API failures
# Check: API keys, rate limits, network connectivity

# 4. Performance issues
# Use: profiling tools, query analysis, caching strategies
```

#### Debugging Tools
```python
# Logging
import logging
logger = logging.getLogger(__name__)
logger.info("Debug message")

# Debugging with pdb
import pdb; pdb.set_trace()

# Performance profiling
import cProfile
cProfile.run('your_function()')

# Memory profiling
from memory_profiler import profile

@profile
def your_function():
    pass
```

### Mobile Debugging

#### Common Issues
```typescript
// 1. Navigation issues
// Check: route names, navigation parameters, stack structure

// 2. State management issues
// Check: context providers, hook dependencies, state updates

// 3. Performance issues
// Check: unnecessary re-renders, large lists, image optimization

// 4. Network issues
// Check: API endpoints, error handling, offline support
```

#### Debugging Tools
```typescript
// React DevTools
// Flipper (for React Native debugging)
// Console.log statements
// React Native Debugger

// Performance monitoring
import { Performance } from 'react-native';

Performance.mark('start_operation');
// ... your code
Performance.mark('end_operation');
Performance.measure('operation_duration', 'start_operation', 'end_operation');
```

## Performance Guidelines

### Backend Performance

#### Database Optimization
```python
# Use indexes effectively
# Implement connection pooling
# Use query optimization
# Implement caching strategies

# Example: Efficient query
def get_user_documents(user_id: str, limit: int = 10):
    return db.query(Document)\
             .filter(Document.user_id == user_id)\
             .order_by(Document.created_at.desc())\
             .limit(limit)\
             .all()
```

#### API Performance
```python
# Use async/await properly
# Implement pagination
# Use response compression
# Implement rate limiting

# Example: Efficient endpoint
@router.get("/documents")
async def get_documents(
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * limit
    documents = await document_service.get_user_documents(
        current_user.id, 
        limit=limit, 
        offset=offset
    )
    return documents
```

### Mobile Performance

#### React Optimization
```typescript
// Use React.memo for component memoization
const MemoizedComponent = React.memo(({ data }) => {
  return <div>{data.name}</div>;
});

// Use useMemo for expensive calculations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// Use useCallback for function references
const handleClick = useCallback(() => {
  onItemClick(item.id);
}, [item.id, onItemClick]);
```

#### List Optimization
```typescript
// Use FlatList for large lists
<FlatList
  data={items}
  renderItem={renderItem}
  keyExtractor={(item) => item.id}
  getItemLayout={(data, index) => ({
    length: ITEM_HEIGHT,
    offset: ITEM_HEIGHT * index,
    index,
  })}
  removeClippedSubviews={true}
  maxToRenderPerBatch={10}
  windowSize={10}
/>
```

## Security Best Practices

### Backend Security

#### Authentication & Authorization
```python
# Use JWT tokens properly
# Implement rate limiting
# Validate all inputs
# Use parameterized queries

# Example: Secure endpoint
@router.get("/secure-data")
async def get_secure_data(
    current_user: User = Depends(get_current_user)
):
    # User is authenticated and authorized
    return {"data": "secure information"}
```

#### Data Protection
```python
# Encrypt sensitive data
# Use HTTPS everywhere
# Implement proper error handling
# Log security events

# Example: Data encryption
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str) -> str:
    key = os.environ.get('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()
```

### Mobile Security

#### Data Protection
```typescript
// Use SecureStore for sensitive data
import * as SecureStore from 'expo-secure-store';

const storeSecureData = async (key: string, value: string) => {
  await SecureStore.setItemAsync(key, value);
};

// Implement proper authentication
// Use certificate pinning
// Validate all inputs
```

## Deployment Guide

### Backend Deployment

#### Development Deployment
```bash
# Using Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Using direct Python
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

#### Production Deployment
```bash
# Build Docker image
docker build -t personal-db-backend .

# Deploy to production
kubectl apply -f k8s/
```

### Mobile Deployment

#### Development Build
```bash
# Build for development
eas build --profile development --platform all

# Preview build
eas build --profile preview --platform all
```

#### Production Deployment
```bash
# Production build
eas build --profile production --platform all

# Submit to app stores
eas submit --platform ios
eas submit --platform android

# OTA updates
eas update --branch production
```

## Resources & References

### Documentation
- [Backend Architecture](./BACKEND.md)
- [Mobile Architecture](./MOBILE.md)
- [Data Pipeline](./DATA_PIPELINE.md)
- [Database Schema](./DATABASE_SCHEMA.md)
- [Deployment Guide](./DEPLOYMENT.md)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Native Documentation](https://reactnative.dev/)
- [Expo Documentation](https://docs.expo.dev/)
- [Supabase Documentation](https://supabase.com/docs)
- [Pinecone Documentation](https://docs.pinecone.io/)

### Team Communication
- **Slack:** #personal-db-development
- **Code Reviews:** GitHub/GitLab PRs
- **Standups:** Daily at 10:00 AM
- **Sprint Planning:** Bi-weekly on Mondays

## Getting Help

### First Steps When Stuck
1. **Check documentation** first
2. **Search existing issues** in the repository
3. **Ask in team chat** for quick questions
4. **Create a detailed issue** for complex problems
5. **Schedule a pair programming session** if needed

### Issue Reporting Template
```markdown
## Issue Description
Brief description of the issue

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., macOS 14.0]
- Python/Node version: [e.g., Python 3.14, Node 18]
- Browser/Device: [if applicable]

## Additional Context
Any other relevant information
```

---

Welcome to the team! We're excited to have you contributing to Personal Database Mobile. Don't hesitate to reach out if you need any help getting started.

*This documentation is proprietary and confidential. All rights reserved.*
