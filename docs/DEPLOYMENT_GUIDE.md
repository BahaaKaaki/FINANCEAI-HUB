# Deployment Guide

## Overview

This guide covers deploying the AI Financial Data System in various environments, from local development to production-ready deployments with Docker, cloud platforms, and enterprise configurations.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Production Configuration](#production-configuration)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Considerations](#security-considerations)
7. [Scaling and Performance](#scaling-and-performance)
8. [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- At least 4GB RAM
- 2GB free disk space

### Installation Steps

1. **Clone the Repository**
```bash
git clone <https://github.com/BahaaKaaki/FinanceAI-Hub>
```

2. **Create Virtual Environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your configuration
# Required: At least one LLM provider API key
OPENAI_API_KEY=openai_api_key
# OR
ANTHROPIC_API_KEY=anthropic_api_key
# OR
GROQ_API_KEY=groq_api_key
```

5. **Initialize Database**
```bash
python -c "from app.database.connection import create_tables; create_tables()"
```

6. **Start Development Server**
```bash
# Using the run script (recommended)
python run.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **Verify Installation**
```bash
# Check health endpoint
curl http://localhost:8000/health

# Access interactive documentation
open http://localhost:8000/docs
```

### Development Environment Variables

```bash
# .env file for development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./financial_data.db
DATABASE_ECHO=true

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=key_here
OPENAI_MODEL=gpt-4o-mini
TEMPERATURE=0.1

# CORS for development
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

## Docker Deployment

### Single Container Deployment

1. **Create Dockerfile**
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Build and Run**
```bash
# Build image
docker build -t ai-financial-data-system .

# Run container
docker run -d \
  --name financial-data-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=ey_here \
  -e DATABASE_URL=sqlite:///./data/financial_data.db \
  -v $(pwd)/data:/app/data \
  ai-financial-data-system
```

### Docker Compose Deployment

1. **Create docker-compose.yml**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/financial_data
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=financial_data
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

2. **Create .env file**
```bash
# .env for Docker Compose
OPENAI_API_KEY=key_here
POSTGRES_PASSWORD=secure_password
```

3. **Deploy with Docker Compose**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Scale API service
docker-compose up -d --scale api=3
```

### Production Docker Configuration

1. **Multi-stage Dockerfile**
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Create app user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app
COPY --chown=app:app . .

USER app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Cloud Deployment

### AWS Deployment

#### Using AWS ECS with Fargate

1. **Create Task Definition**
```json
{
  "family": "ai-financial-data-system",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/ai-financial-data-system:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/financial_data"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ai-financial-data-system",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

2. **Create ECS Service**
```bash
aws ecs create-service \
  --cluster production-cluster \
  --service-name ai-financial-data-system \
  --task-definition ai-financial-data-system:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### Using AWS Lambda (Serverless)

1. **Install Mangum for ASGI**
```bash
pip install mangum
```

2. **Create Lambda Handler**
```python
# lambda_handler.py
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
```

3. **Deploy with AWS SAM**
```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  FinancialDataAPI:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: lambda_handler.handler
      Runtime: python3.11
      Timeout: 30
      MemorySize: 1024
      Environment:
        Variables:
          DATABASE_URL: !Ref DatabaseURL
          OPENAI_API_KEY: !Ref OpenAIKey
      Events:
        ApiGateway:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY
```

### Google Cloud Platform

#### Using Cloud Run

1. **Create cloudbuild.yaml**
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-financial-data-system', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ai-financial-data-system']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'ai-financial-data-system'
      - '--image'
      - 'gcr.io/$PROJECT_ID/ai-financial-data-system'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
```

2. **Deploy to Cloud Run**
```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Set environment variables
gcloud run services update ai-financial-data-system \
  --set-env-vars DATABASE_URL=postgresql://... \
  --set-env-vars OPENAI_API_KEY=your_key
```

### Azure Deployment

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name financial-data-rg --location eastus

# Deploy container
az container create \
  --resource-group financial-data-rg \
  --name ai-financial-data-system \
  --image your-registry/ai-financial-data-system:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL=postgresql://... \
    OPENAI_API_KEY=your_key \
  --restart-policy Always
```

## Production Configuration

### Environment Variables

```bash
# Production .env
DEBUG=false
LOG_LEVEL=INFO
APP_NAME="AI Financial Data System"

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:password@host:5432/financial_data
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_ECHO=false

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your_production_key
OPENAI_MODEL=gpt-4
MAX_TOKENS=4000
TEMPERATURE=0.1

# Security
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=["https://yourdomain.com"]
ALLOWED_HOSTS=["yourdomain.com", "api.yourdomain.com"]

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
WORKER_PROCESSES=4

# Caching
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Monitoring
SENTRY_DSN=your_sentry_dsn
METRICS_ENABLED=true
```

### Database Configuration

#### PostgreSQL Setup

1. **Create Database**
```sql
CREATE DATABASE financial_data;
CREATE USER financial_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE financial_data TO financial_user;
```

2. **Connection Pooling**
```python
# app/core/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

3. **Database Migrations**
```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Load Balancer Configuration

#### Nginx Configuration

```nginx
# nginx.conf
upstream api_servers {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://api_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Health checks
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }

    location /health {
        access_log off;
        proxy_pass http://api_servers;
    }
}
```

## Monitoring and Observability

### Health Checks

```python
# app/core/monitoring.py
from app.database.connection import check_database_connection
from app.ai.llm_client import check_llm_connection

def comprehensive_health_check():
    checks = {
        "database": check_database_connection(),
        "llm_service": check_llm_connection(),
        "disk_space": check_disk_space(),
        "memory_usage": check_memory_usage()
    }
    
    overall_status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Logging Configuration

```python
# app/core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/financial-data-api.log')
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### Metrics Collection

```python
# app/core/metrics.py
import time
import psutil
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.request_counts = defaultdict(int)
        self.response_times = []
        self.error_counts = defaultdict(int)
    
    def record_request(self, endpoint, method, status_code, response_time):
        self.request_counts[f"{method} {endpoint}"] += 1
        self.response_times.append(response_time)
        
        if status_code >= 400:
            self.error_counts[status_code] += 1
    
    def get_system_metrics(self):
        return {
            "cpu_usage_percent": psutil.cpu_percent(),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "active_connections": len(psutil.net_connections()),
        }
    
    def get_application_metrics(self):
        return {
            "total_requests": sum(self.request_counts.values()),
            "average_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "error_rate": sum(self.error_counts.values()) / sum(self.request_counts.values()) if self.request_counts else 0,
            "requests_per_endpoint": dict(self.request_counts)
        }
```

### Alerting

```python
# app/core/alerts.py
import smtplib
from email.mime.text import MIMEText

class AlertManager:
    def __init__(self, smtp_server, smtp_port, username, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_alert(self, subject, message, recipients):
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
    
    def check_and_alert(self, metrics):
        if metrics['cpu_usage_percent'] > 80:
            self.send_alert(
                "High CPU Usage Alert",
                f"CPU usage is at {metrics['cpu_usage_percent']}%",
                ["admin@yourdomain.com"]
            )
        
        if metrics['error_rate'] > 0.05:  # 5% error rate
            self.send_alert(
                "High Error Rate Alert",
                f"Error rate is at {metrics['error_rate']*100:.1f}%",
                ["admin@yourdomain.com"]
            )
```

## Security Considerations

### API Security

1. **Rate Limiting**
```python
# app/core/rate_limiting.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/financial-data")
@limiter.limit("100/minute")
async def get_financial_data(request: Request):
    # Endpoint implementation
    pass
```

2. **Input Validation**
```python
# app/core/validation.py
from pydantic import BaseModel, validator
import re

class QueryRequest(BaseModel):
    query: str
    
    @validator('query')
    def validate_query(cls, v):
        if len(v) > 1000:
            raise ValueError('Query too long')
        
        # Prevent SQL injection patterns
        dangerous_patterns = ['DROP', 'DELETE', 'UPDATE', 'INSERT', '--', ';']
        if any(pattern in v.upper() for pattern in dangerous_patterns):
            raise ValueError('Invalid query content')
        
        return v
```

3. **HTTPS Configuration**
```python
# app/core/security.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Force HTTPS in production
if not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=settings.ALLOWED_HOSTS
)
```

### Data Security

1. **Environment Variables**
```bash
# Use secrets management in production
export OPENAI_API_KEY=$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString --output text)
```

2. **Database Security**
```python
# Use connection encryption
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

3. **API Key Rotation**
```python
# app/core/key_rotation.py
import os
from datetime import datetime, timedelta

class KeyRotationManager:
    def __init__(self):
        self.rotation_interval = timedelta(days=30)
        self.last_rotation = datetime.utcnow()
    
    def should_rotate_keys(self):
        return datetime.utcnow() - self.last_rotation > self.rotation_interval
    
    def rotate_api_keys(self):
        # Implement key rotation logic
        pass
```

## Scaling and Performance

### Horizontal Scaling

1. **Load Balancing**
```yaml
# docker-compose.yml for scaling
version: '3.8'
services:
  api:
    build: .
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://...
    depends_on:
      - db
      - redis
```

2. **Database Read Replicas**
```python
# app/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Master database for writes
master_engine = create_engine(settings.DATABASE_WRITE_URL)
MasterSession = sessionmaker(bind=master_engine)

# Read replica for reads
replica_engine = create_engine(settings.DATABASE_READ_URL)
ReplicaSession = sessionmaker(bind=replica_engine)

def get_read_session():
    return ReplicaSession()

def get_write_session():
    return MasterSession()
```

### Caching Strategy

1. **Redis Caching**
```python
# app/core/cache.py
import redis
import json
from typing import Optional, Any

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
    
    def get(self, key: str) -> Optional[Any]:
        value = self.redis_client.get(key)
        return json.loads(value) if value else None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        self.redis_client.setex(key, ttl, json.dumps(value))
    
    def delete(self, key: str):
        self.redis_client.delete(key)
```

2. **Application-Level Caching**
```python
# app/core/decorators.py
from functools import wraps
import hashlib

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

### Performance Optimization

1. **Database Query Optimization**
```python
# app/database/queries.py
from sqlalchemy.orm import selectinload, joinedload

def get_financial_records_optimized(session, filters):
    query = session.query(FinancialRecord)\
        .options(
            selectinload(FinancialRecord.account_values),
            joinedload(FinancialRecord.accounts)
        )\
        .filter_by(**filters)
    
    return query.all()
```

2. **Async Processing**
```python
# app/services/async_processing.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncProcessor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_files_async(self, file_paths):
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self.process_file, file_path)
            for file_path in file_paths
        ]
        return await asyncio.gather(*tasks)
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
```bash
# Check database connectivity
python -c "from app.database.connection import check_database_connection; print(check_database_connection())"

# Check database logs
docker logs financial-data-db
```

2. **LLM API Issues**
```bash
# Test LLM connectivity
python -c "from app.ai.llm_client import LLMClient; client = LLMClient(); print(client.test_connection())"

# Check API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

3. **Memory Issues**
```bash
# Monitor memory usage
docker stats financial-data-api

# Check for memory leaks
python -m memory_profiler app/main.py
```

### Debugging Tools

1. **Health Check Script**
```python
#!/usr/bin/env python3
# scripts/health_check.py
import requests
import sys

def check_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
```

2. **Log Analysis**
```bash
# scripts/analyze_logs.sh
#!/bin/bash

# Find errors in logs
grep -i error /var/log/financial-data-api.log | tail -20

# Check response times
grep "response_time" /var/log/financial-data-api.log | awk '{print $NF}' | sort -n | tail -10

# Count requests by endpoint
grep "GET\|POST" /var/log/financial-data-api.log | awk '{print $3}' | sort | uniq -c | sort -nr
```

### Performance Monitoring

1. **Resource Monitoring**
```python
# scripts/monitor_resources.py
import psutil
import time

def monitor_resources():
    while True:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        print(f"CPU: {cpu}% | Memory: {memory}% | Disk: {disk}%")
        
        if cpu > 80 or memory > 80:
            print("⚠️  High resource usage detected!")
        
        time.sleep(60)

if __name__ == "__main__":
    monitor_resources()
```

This deployment guide provides everything needed to deploy the AI Financial Data System in various environments, from development to production-scale deployments (Note that we only cover local and render deployments for now)