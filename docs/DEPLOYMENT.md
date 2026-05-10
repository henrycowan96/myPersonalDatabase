# Deployment & Environment Setup Documentation

## Overview

This document provides comprehensive guidance for deploying and configuring the Personal Database Mobile system across different environments. It covers development, staging, and production deployments with security best practices and operational procedures.

## Environment Architecture

### Environment Tiers

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Development   │    │    Staging      │    │   Production    │
│                 │    │                 │    │                 │
│ • Local Dev     │    │ • Cloud Test    │    │ • Cloud Prod    │
│ • Mock Services │    │ • Real APIs     │    │ • Full Scale    │
│ • Debug Mode    │    │ • Performance   │    │ • High Security │
│ • Hot Reload    │    │ • Integration   │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Infrastructure Components

#### Backend Infrastructure
- **Application Server:** FastAPI on Python 3.14+
- **Database:** Supabase (PostgreSQL) + Pinecone (Vector DB)
- **Cache:** Redis for session and query caching
- **File Storage:** AWS S3 or equivalent
- **Load Balancer:** Nginx or cloud load balancer
- **CDN:** CloudFlare or AWS CloudFront

#### Mobile Infrastructure
- **Build System:** Expo Application Services (EAS)
- **App Stores:** Apple App Store & Google Play Store
- **Analytics:** Segment or Mixpanel
- **Crash Reporting:** Sentry or Crashlytics
- **Push Notifications:** Expo Push Notifications

## Development Environment Setup

### Prerequisites

#### System Requirements
```bash
# Operating System
- macOS 13+ (for Apple ecosystem integration)
- Ubuntu 20.04+ or Windows 11+ (alternative)

# Software Requirements
- Python 3.14+
- Node.js 18+
- npm or yarn
- Git
- Docker (optional but recommended)
- Xcode (for iOS development)
- Android Studio (for Android development)
```

#### Development Tools
```bash
# Python Development
pip install virtualenv
pip install poetry  # Recommended for dependency management

# Mobile Development
npm install -g @expo/cli
npm install -g eas-cli

# Database Tools
# PostgreSQL client (psql or TablePlus)
# Redis client (redis-cli)
```

### Backend Setup

#### 1. Repository Setup
```bash
# Clone repository
git clone https://github.com/company/personal-database-mobile.git
cd personal-database-mobile

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Configure environment variables
nano .env
```

#### 3. Environment Variables (.env)
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/personal_db
REDIS_URL=redis://localhost:6379/0

# External Services
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=personal-database
OPENROUTER_API_KEY=your_openrouter_api_key

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Security
SECRET_KEY=your_super_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Development Settings
DEBUG=true
LOG_LEVEL=debug
CORS_ORIGINS=http://localhost:3000,http://localhost:8081

# File Storage
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE=50MB
```

#### 4. Database Setup
```bash
# Run database migrations
python -m alembic upgrade head

# Initialize Pinecone index
python scripts/init_pinecone.py

# Load sample data (optional)
python scripts/load_sample_data.py
```

#### 5. Development Server
```bash
# Start backend server
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000

# Or use the main orchestration script
python main.py --mobile --skip-extraction --skip-processing
```

### Mobile App Setup

#### 1. Mobile App Dependencies
```bash
# Navigate to mobile app directory
cd "My Personal Database Mobile"

# Install dependencies
npm install

# Install Expo CLI globally
npm install -g @expo/cli

# Login to Expo
expo login
```

#### 2. Mobile Environment Configuration
```bash
# Create environment file
echo "EXPO_PUBLIC_API_URL=http://localhost:8000" > .env.local

# For production builds
echo "EXPO_PUBLIC_API_URL=https://api.personaldatabase.com" > .env.production
```

#### 3. Mobile Development Server
```bash
# Start Expo development server
npx expo start

# Start with specific platform
npx expo start --ios
npx expo start --android
```

## Staging Environment Setup

### Cloud Infrastructure

#### 1. Cloud Provider Setup (AWS Example)
```bash
# Using AWS CLI
aws configure

# Create infrastructure using Terraform
cd infrastructure/staging
terraform init
terraform plan
terraform apply
```

#### 2. Docker Configuration
```dockerfile
# Dockerfile for backend
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 3. Docker Compose (Staging)
```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
    restart: unless-stopped
```

### CI/CD Pipeline

#### GitHub Actions Configuration
```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [staging]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
          
      - name: Run tests
        run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to staging
        run: |
          # Deployment commands
          docker build -t personal-db-staging .
          docker push ${{ secrets.REGISTRY_URL }}/personal-db-staging
          
      - name: Run database migrations
        run: |
          # Migration commands
```

## Production Environment Setup

### Security Configuration

#### 1. SSL/TLS Configuration
```nginx
# nginx.conf for production
server {
    listen 443 ssl http2;
    server_name api.personaldatabase.com;
    
    # SSL certificates
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2. Environment Security
```bash
# Production environment variables (secure storage)
# Use AWS Secrets Manager, Azure Key Vault, or similar

# Database
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}

# External APIs
PINECONE_API_KEY=${PINECONE_API_KEY}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}

# Authentication
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
SECRET_KEY=${SECRET_KEY}

# Production settings
DEBUG=false
LOG_LEVEL=info
CORS_ORIGINS=https://app.personaldatabase.com
```

### Scaling Configuration

#### 1. Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: personal-db-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: personal-db-backend
  template:
    metadata:
      labels:
        app: personal-db-backend
    spec:
      containers:
      - name: backend
        image: personal-db:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 2. Auto-scaling Configuration
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: personal-db-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: personal-db-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Mobile App Deployment

### Build Configuration

#### 1. Expo Application Services (EAS)
```json
// eas.json
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "ios": {
        "autoIncrement": true
      },
      "android": {
        "autoIncrement": true
      }
    }
  },
  "submit": {
    "production": {}
  }
}
```

#### 2. App Store Configuration
```json
// app.json production settings
{
  "expo": {
    "name": "Personal Database",
    "slug": "personal-database",
    "version": "1.0.0",
    "orientation": "portrait",
    "platforms": ["ios", "android"],
    "ios": {
      "bundleIdentifier": "com.company.personaldatabase",
      "buildNumber": "1.0.0",
      "supportsTablet": true,
      "config": {
        "usesNonExemptEncryption": false
      }
    },
    "android": {
      "package": "com.company.personaldatabase",
      "versionCode": 1,
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#FFFFFF"
      }
    },
    "extra": {
      "eas": {
        "projectId": "your-project-id"
      }
    }
  }
}
```

### Build & Release Process

#### 1. Development Build
```bash
# Build for development
eas build --profile development --platform all

# Build for preview/testing
eas build --profile preview --platform all
```

#### 2. Production Build
```bash
# Build for production
eas build --profile production --platform all

# Submit to app stores
eas submit --platform ios
eas submit --platform android
```

#### 3. Over-the-Air Updates
```bash
# Deploy OTA update
eas update --branch production --message "Bug fixes and improvements"
```

## Monitoring & Observability

### 1. Application Monitoring

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'personal-db-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

#### Metrics Collection
```python
# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active database connections')

# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response
```

### 2. Logging Configuration

#### Structured Logging
```python
# app/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/personal-db/app.log')
    ]
)

logger = logging.getLogger(__name__)
logger.handlers[0].setFormatter(JSONFormatter())
```

### 3. Error Tracking

#### Sentry Integration
```python
# app/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry():
    sentry_sdk.init(
        dsn="your-sentry-dsn",
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development")
    )
```

## Backup & Disaster Recovery

### 1. Database Backup Strategy

#### Automated Backups
```bash
#!/bin/bash
# backup.sh

# Database backup
pg_dump $DATABASE_URL > /backups/db_backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backups
gzip /backups/db_backup_*.sql

# Upload to cloud storage
aws s3 sync /backups/ s3://personal-db-backups/

# Clean old backups (keep 30 days)
find /backups/ -name "*.sql.gz" -mtime +30 -delete
```

#### Backup Restoration
```bash
#!/bin/bash
# restore.sh

# Download backup from cloud storage
aws s3 cp s3://personal-db-backups/db_backup_20240101_120000.sql.gz /tmp/

# Extract backup
gunzip /tmp/db_backup_20240101_120000.sql.gz

# Restore database
psql $DATABASE_URL < /tmp/db_backup_20240101_120000.sql
```

### 2. Vector Database Backup

#### Pinecone Backup Strategy
```python
# scripts/backup_pinecone.py
import pinecone
import json
from datetime import datetime

def backup_pinecone_index():
    """Backup Pinecone index data"""
    pinecone.init(api_key=PINECONE_API_KEY)
    index = pinecone.Index(PINECONE_INDEX_NAME)
    
    # Fetch all vectors (in batches)
    all_vectors = []
    for ids in index.list():  # This is a simplified example
        vectors = index.fetch(ids=ids)
        all_vectors.extend(vectors['vectors'])
    
    # Save backup
    backup_file = f"pinecone_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, 'w') as f:
        json.dump(all_vectors, f)
    
    print(f"Backup saved to {backup_file}")
```

## Security Hardening

### 1. Network Security

#### Firewall Configuration
```bash
# UFW firewall rules
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

#### VPN Configuration
```bash
# WireGuard configuration example
[Interface]
PrivateKey = server_private_key
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = client_public_key
AllowedIPs = 10.0.0.2/32
```

### 2. Application Security

#### Security Headers
```python
# app/security.py
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# Trusted hosts middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.personaldatabase.com", "*.personaldatabase.com"]
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
```

## Performance Optimization

### 1. Caching Strategy

#### Redis Configuration
```python
# app/cache.py
import redis
import json
from typing import Optional, Any

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        value = self.redis_client.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        self.redis_client.setex(key, ttl, json.dumps(value))
    
    async def delete(self, key: str):
        self.redis_client.delete(key)
```

### 2. Database Optimization

#### Connection Pooling
```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

---

*This documentation is proprietary and confidential. All rights reserved.*
